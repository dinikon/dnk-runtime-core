"""Offline contract tests for both chart entrypoints. Requires Helm 3 and PyYAML.

Run: HELM=/path/to/helm python -m unittest discover -s deploy/helm/tests -v
All generated values, rendered manifests and packages stay in temporary directories.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[3]
UMBRELLA = ROOT / "deploy/helm/dnk-runtime-core"
CORE = UMBRELLA / "charts/core"
HELM = os.environ.get("HELM", "helm")
SECRET_KEY = "render-test-signing-key-0123456789-abcdefghijklmnopqrstuvwxyz"
FERNET_KEY = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
PG_PASSWORD = "render-test-postgres-password"
REDIS_PASSWORD = "render-test-redis-password"


def core_values(pg=True, redis=True, existing=False, ingress=False):
    """Non-production fixtures; never substitute these credentials in deployments."""

    def secret(value, key):
        if existing:
            return {"existingSecret": {"name": "core-test-secrets", "key": key}}
        return {"value": value}

    return {
        "application": {
            "server": {"publicOrigin": "https://core.example.test"},
            "security": {"secretKey": secret(SECRET_KEY, "django")},
            "mfa": {"encryptionKey": secret(FERNET_KEY, "fernet")},
            "email": {
                "host": "smtp.example.test",
                "from": "identity@example.test",
            },
        },
        "backend": {"image": {"tag": "test"}},
        "frontend": {"image": {"tag": "test"}},
        "gateway": {"image": {"tag": "test"}},
        "postgresql": {
            "enabled": pg,
            "auth": {"password": secret(PG_PASSWORD, "postgres")},
            "external": {"host": "postgres.example.test"} if not pg else {},
        },
        "redis": {
            "enabled": redis,
            "auth": {"password": secret(REDIS_PASSWORD, "redis")},
            "external": {"host": "redis.example.test"} if not redis else {},
        },
        "ingress": {
            "enabled": ingress,
            "className": "nginx" if ingress else "",
            "tls": {"secretName": "core-test-tls"} if ingress else {},
        },
    }


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate keys that ordinary YAML loading silently overwrites."""

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise yaml.constructor.ConstructorError(
                    "while constructing mapping",
                    node.start_mark,
                    "duplicate key: " + str(key),
                    key_node.start_mark,
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def component(resource):
    return (
        resource.get("metadata", {})
        .get("labels", {})
        .get("app.kubernetes.io/component")
    )


def podspec(resource):
    return resource["spec"]["template"]["spec"]


class HelmContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which(HELM) is None:
            raise RuntimeError(
                "Helm is required; install it or set HELM to its executable path"
            )

    def run_helm(
        self, chart, values, command="template", success=True, release="contract"
    ):
        with tempfile.TemporaryDirectory(prefix="dnk-helm-render-") as directory:
            values_file = Path(directory) / "values.yaml"
            values_file.write_text(
                yaml.safe_dump({"core": values} if chart == UMBRELLA else values)
            )
            arguments = [HELM, command]
            if command == "template":
                arguments += [release]
            arguments += [str(chart), "-f", str(values_file)]
            if command == "lint":
                arguments.append("--strict")
            result = subprocess.run(arguments, text=True, capture_output=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        else:
            self.assertNotEqual(
                result.returncode, 0, "invalid configuration unexpectedly rendered"
            )
        return result

    def render(self, values, chart=CORE):
        return [
            item
            for item in yaml.load_all(
                self.run_helm(chart, values).stdout, Loader=UniqueKeyLoader
            )
            if item
        ]

    def assert_contract(self, manifests, pg, redis, existing, ingress):
        deployments = [r for r in manifests if r["kind"] == "Deployment"]
        self.assertEqual(
            {component(r) for r in deployments}, {"backend", "frontend", "gateway"}
        )
        statefulsets = [r for r in manifests if r["kind"] == "StatefulSet"]
        self.assertEqual(len(statefulsets), int(pg) + int(redis))
        self.assertEqual(
            {component(r) for r in statefulsets},
            {
                name
                for name, enabled in [("postgresql", pg), ("redis", redis)]
                if enabled
            },
        )
        configs = {
            r["metadata"]["name"]: r for r in manifests if r["kind"] == "ConfigMap"
        }
        secrets = {r["metadata"]["name"]: r for r in manifests if r["kind"] == "Secret"}
        services = {
            r["metadata"]["name"]: r for r in manifests if r["kind"] == "Service"
        }
        self.assertEqual(
            {
                component(r)
                for r in services.values()
                if component(r) in {"backend", "frontend", "gateway"}
            },
            {"backend", "frontend", "gateway"},
        )
        non_secret_text = yaml.safe_dump(
            [r for r in manifests if r["kind"] != "Secret"]
        )
        for value in [SECRET_KEY, FERNET_KEY, PG_PASSWORD, REDIS_PASSWORD]:
            self.assertNotIn(value, non_secret_text)
        if existing:
            self.assertFalse(
                secrets, "external secrets must not be recreated or copied"
            )

        def resolve_env(container):
            env = {}
            for source in container.get("envFrom", []):
                if "configMapRef" in source:
                    env.update(configs[source["configMapRef"]["name"]]["data"])
            for entry in container.get("env", []):
                self.assertNotIn(entry["name"], env, "duplicate environment variable")
                env[entry["name"]] = entry.get("value", entry.get("valueFrom"))
                ref = entry.get("valueFrom", {}).get("secretKeyRef")
                if ref:
                    if existing:
                        self.assertEqual(ref["name"], "core-test-secrets")
                    else:
                        self.assertIn(ref["name"], secrets)
                        self.assertIn(
                            ref["key"],
                            secrets[ref["name"]].get("data", {})
                            | secrets[ref["name"]].get("stringData", {}),
                        )
            return env

        for deployment in deployments:
            spec = podspec(deployment)
            annotations = deployment["spec"]["template"]["metadata"]["annotations"]
            self.assertTrue(any(key.startswith("checksum/") for key in annotations))
            for container in spec["containers"]:
                env = resolve_env(container)
                for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
                    self.assertIn(probe, container)
                if component(deployment) == "backend":
                    self.assertEqual(
                        env["CORE_PUBLIC_ORIGIN"], "https://core.example.test"
                    )
                    self.assertEqual(env["CORE_DEBUG"], "false")
                    self.assertEqual(env["CORE_SESSION_COOKIE_AGE"], "1209600")
                    self.assertEqual(env["CORE_DB_HOST"] in services, pg)
                    self.assertEqual(env["CORE_REDIS_HOST"] in services, redis)
                    self.assertIn("secretKeyRef", env["CORE_SECRET_KEY"])
                    self.assertIn("secretKeyRef", env["CORE_MFA_ENCRYPTION_KEY"])
                    for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
                        http = container[probe]["httpGet"]
                        self.assertEqual(http["path"], "/api/capabilities/")
                        headers = {
                            h["name"].lower(): h["value"] for h in http["httpHeaders"]
                        }
                        self.assertEqual(headers["host"], "core.example.test")
                        self.assertEqual(headers["x-forwarded-proto"], "https")
                    initializers = spec["initContainers"]
                    self.assertEqual(len(initializers), 1)
                    initializer = initializers[0]
                    self.assertEqual(initializer["image"], container["image"])
                    self.assertIn(
                        "prepare_deployment",
                        initializer.get("command", []) + initializer.get("args", []),
                    )
                    self.assertEqual(resolve_env(initializer), env)
                elif component(deployment) == "frontend":
                    self.assertEqual(
                        env["NUXT_PUBLIC_SITE_URL"], "https://core.example.test"
                    )
                    self.assertEqual(
                        container["readinessProbe"]["httpGet"]["path"], "/"
                    )

        gateway_config = "\n".join(
            str(value)
            for config in configs.values()
            for value in config.get("data", {}).values()
            if "proxy_pass" in str(value)
        )
        self.assertIn("api|accounts|admin|static", gateway_config)
        self.assertNotIn("127.0.0.11", gateway_config)
        self.assertIn("X-Forwarded-Proto", gateway_config)
        for deployment in deployments:
            if component(deployment) in ("backend", "frontend"):
                self.assertIn(deployment["metadata"]["name"], gateway_config)

        for statefulset in statefulsets:
            self.assertTrue(statefulset["spec"]["volumeClaimTemplates"])
            self.assertEqual(
                statefulset["spec"]
                .get("persistentVolumeClaimRetentionPolicy", {})
                .get("whenDeleted", "Retain"),
                "Retain",
            )
        ingresses = [r for r in manifests if r["kind"] == "Ingress"]
        self.assertEqual(len(ingresses), int(ingress))
        if ingress:
            spec = ingresses[0]["spec"]
            self.assertEqual(spec["rules"][0]["host"], "core.example.test")
            self.assertEqual(
                spec["tls"],
                [{"hosts": ["core.example.test"], "secretName": "core-test-tls"}],
            )
            self.assertEqual(spec["ingressClassName"], "nginx")
            gateway = next(r for r in deployments if component(r) == "gateway")
            self.assertEqual(
                spec["rules"][0]["http"]["paths"][0]["backend"]["service"]["name"],
                gateway["metadata"]["name"],
            )

    def test_deployment_matrix(self):
        for chart in [UMBRELLA, CORE]:
            for pg in [True, False]:
                for redis in [True, False]:
                    for existing in [False, True]:
                        for ingress in [False, True]:
                            with self.subTest(
                                chart=chart.name,
                                pg=pg,
                                redis=redis,
                                existing=existing,
                                ingress=ingress,
                            ):
                                self.assert_contract(
                                    self.render(
                                        core_values(pg, redis, existing, ingress), chart
                                    ),
                                    pg,
                                    redis,
                                    existing,
                                    ingress,
                                )

    def test_disabled_core_needs_no_deployment_configuration(self):
        self.assertEqual(self.render({"enabled": False}, UMBRELLA), [])

    def test_lint_and_package_both_entrypoints(self):
        for chart in [UMBRELLA, CORE]:
            with self.subTest(chart=chart.name):
                self.run_helm(chart, core_values(), command="lint")
                with tempfile.TemporaryDirectory(
                    prefix="dnk-helm-package-"
                ) as directory:
                    result = subprocess.run(
                        [HELM, "package", str(chart), "--destination", directory],
                        text=True,
                        capture_output=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    package = next(Path(directory).glob("*.tgz"))
                    self.run_helm(
                        package,
                        core_values() if chart == CORE else {"core": core_values()},
                    )

    def test_external_redis_url_secret(self):
        values = core_values(redis=False)
        values["redis"]["external"] = {
            "url": {"existingSecret": {"name": "redis-url", "key": "url"}}
        }
        values["redis"]["auth"]["password"] = {"value": ""}
        manifests = self.render(values)
        backend = next(
            r
            for r in manifests
            if r["kind"] == "Deployment" and component(r) == "backend"
        )
        env = {e["name"]: e for e in podspec(backend)["containers"][0]["env"]}
        self.assertEqual(
            env["CORE_REDIS_URL"]["valueFrom"]["secretKeyRef"],
            {"name": "redis-url", "key": "url"},
        )

    def test_custom_env_and_migrations_opt_out(self):
        values = core_values()
        values["migrations"] = {"enabled": False}
        values["backend"]["extraEnv"] = [
            {"name": "CUSTOM_VALUE", "value": "plain"},
            {
                "name": "CUSTOM_SECRET",
                "valueFrom": {"secretKeyRef": {"name": "additional", "key": "token"}},
            },
        ]
        manifests = self.render(values)
        backend = next(
            r
            for r in manifests
            if r["kind"] == "Deployment" and component(r) == "backend"
        )
        self.assertFalse(podspec(backend).get("initContainers"))
        env = podspec(backend)["containers"][0]["env"]
        for item in values["backend"]["extraEnv"]:
            self.assertIn(item, env)

    def test_configuration_change_restarts_affected_pods(self):
        original = core_values()
        changed = copy.deepcopy(original)
        changed["application"]["server"][
            "publicOrigin"
        ] = "https://changed.example.test"
        first = {
            component(r): r["spec"]["template"]
            for r in self.render(original)
            if r["kind"] == "Deployment"
        }
        second = {
            component(r): r["spec"]["template"]
            for r in self.render(changed)
            if r["kind"] == "Deployment"
        }
        for name in ["backend", "frontend"]:
            self.assertNotEqual(
                first[name]["metadata"]["annotations"],
                second[name]["metadata"]["annotations"],
            )

    def test_empty_dependency_name_override_resolves_to_real_services(self):
        values = core_values()
        values["postgresql"]["nameOverride"] = ""
        values["redis"]["nameOverride"] = ""
        self.assert_contract(self.render(values), True, True, False, False)

    def test_long_release_names_do_not_collide(self):
        names = []
        for suffix in ["b", "c"]:
            result = self.run_helm(CORE, core_values(), release="a" * 51 + "-" + suffix)
            manifests = [
                item
                for item in yaml.load_all(result.stdout, Loader=UniqueKeyLoader)
                if item
            ]
            resource_names = {(r["kind"], r["metadata"]["name"]) for r in manifests}
            self.assertEqual(len(resource_names), len(manifests))
            self.assertTrue(
                all(
                    len(name) <= (63 if kind == "Service" else 253)
                    for kind, name in resource_names
                )
            )
            for statefulset in (r for r in manifests if r["kind"] == "StatefulSet"):
                self.assertIn(
                    ("Service", statefulset["spec"]["serviceName"]), resource_names
                )
            names.append(resource_names)
        self.assertTrue(
            names[0].isdisjoint(names[1]), f"Colliding objects: {names[0] & names[1]}"
        )

    def test_inline_secret_change_restarts_backend(self):
        values = core_values()
        original = next(
            r
            for r in self.render(values)
            if r["kind"] == "Deployment" and component(r) == "backend"
        )
        values["application"]["security"]["secretKey"]["value"] += "-rotated"
        changed = next(
            r
            for r in self.render(values)
            if r["kind"] == "Deployment" and component(r) == "backend"
        )
        self.assertNotEqual(
            original["spec"]["template"]["metadata"]["annotations"],
            changed["spec"]["template"]["metadata"]["annotations"],
        )

    def test_custom_service_ports_and_gateway_rollout(self):
        values = core_values()
        original = next(
            r
            for r in self.render(values)
            if r["kind"] == "Deployment" and component(r) == "gateway"
        )
        values["backend"]["service"] = {"port": 8081}
        values["frontend"]["service"] = {"port": 3001}
        manifests = self.render(values)
        services = {
            component(r): r
            for r in manifests
            if r["kind"] == "Service" and component(r) in {"backend", "frontend"}
        }
        self.assertEqual(services["backend"]["spec"]["ports"][0]["port"], 8081)
        self.assertEqual(services["frontend"]["spec"]["ports"][0]["port"], 3001)
        configuration = next(
            r
            for r in manifests
            if r["kind"] == "ConfigMap" and "default.conf" in r.get("data", {})
        )["data"]["default.conf"]
        self.assertIn(services["backend"]["metadata"]["name"] + ":8081", configuration)
        self.assertIn(services["frontend"]["metadata"]["name"] + ":3001", configuration)
        changed = next(
            r
            for r in manifests
            if r["kind"] == "Deployment" and component(r) == "gateway"
        )
        self.assertNotEqual(
            original["spec"]["template"]["metadata"]["annotations"],
            changed["spec"]["template"]["metadata"]["annotations"],
        )

    def test_invalid_configuration_rejected(self):
        cases = []
        for path in [
            ("application", "server", "publicOrigin"),
            ("application", "security", "secretKey", "value"),
            ("application", "mfa", "encryptionKey", "value"),
            ("backend", "image", "tag"),
            ("frontend", "image", "repository"),
            ("postgresql", "auth", "password", "value"),
            ("redis", "auth", "password", "value"),
        ]:
            values = core_values()
            section = values
            for key in path[:-1]:
                section = section.setdefault(key, {})
            section[path[-1]] = ""
            cases.append(("missing " + ".".join(path), values))
        for origin in [
            "http://core.example.test",
            "https://core.example.test/path",
            "https://user:password@core.example.test",
            "https://core.example.test:0",
            "https://core.example.test:70000",
            "https://core.example.test:invalid",
        ]:
            values = core_values()
            values["application"]["server"]["publicOrigin"] = origin
            cases.append(("invalid origin " + origin, values))
        values = core_values()
        values["application"]["security"]["secretKey"]["existingSecret"] = {
            "name": "duplicate",
            "key": "key",
        }
        cases.append(("two secret sources", values))
        values = core_values()
        values["backend"]["extraEnv"] = [
            {"name": "CORE_SECRET_KEY", "value": "override"}
        ]
        cases.append(("reserved environment override", values))
        values = core_values()
        values["backend"]["extraEnv"] = [
            {"name": "CUSTOM", "value": "1"},
            {"name": "CUSTOM", "value": "2"},
        ]
        cases.append(("duplicate extra environment", values))
        for service in ["postgresql", "redis"]:
            values = core_values(pg=service != "postgresql", redis=service != "redis")
            values[service]["external"]["host"] = ""
            cases.append(("missing external " + service, values))
            values = core_values(pg=service != "postgresql", redis=service != "redis")
            values[service]["external"]["port"] = 70000
            cases.append(("invalid external port " + service, values))
        values = core_values(ingress=True)
        values["ingress"]["tls"]["secretName"] = ""
        cases.append(("missing ingress TLS", values))
        for url in [
            "redis://redis.example.test:0/1",
            "rediss://redis.example.test:70000/1",
            "redis://redis.example.test:invalid/1",
        ]:
            values = core_values(redis=False)
            values["redis"]["external"] = {"url": {"value": url}}
            values["redis"]["auth"]["password"] = {"value": ""}
            cases.append(("invalid Redis URL port", values))
        for workload in ["backend", "frontend", "gateway"]:
            values = core_values()
            values[workload]["pod"] = {"annotations": {"checksum/config": "override"}}
            cases.append(("reserved checksum annotation " + workload, values))
        values = core_values()
        values["application"]["security"]["secretKey"] = {
            "existingSecret": {"name": "partial"}
        }
        cases.append(("partial secret reference", values))
        for label, values in cases:
            with self.subTest(case=label):
                self.run_helm(CORE, values, success=False)


if __name__ == "__main__":
    unittest.main()
