"""Offline Helm contracts; no cluster, network, or real credentials are used.

HELM=/path/to/helm python -m unittest discover -s helm/tests -v
Run helm/build.py before these tests to refresh local chart dependencies.
"""

from __future__ import annotations
import copy
import itertools
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "helm"
HELM = os.environ.get("HELM", "helm")
SECRET_KEY = "render-test-signing-key-0123456789-abcdefghijklmnopqrstuvwxyz"
FERNET_KEY = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
PG_PASSWORD = "render-test-postgres-password"
REDIS_PASSWORD = "render-test-redis-password"
RABBIT_PASSWORD = "render-test-rabbit-password"
CONTROL_KEY = "render-test-control-plane-token"


def secret(value, key, existing=False):
    return (
        {"existingSecret": {"name": "test-secrets", "key": key}}
        if existing
        else {"value": value}
    )


def infrastructure_values(pg=True, redis=True, existing=False):
    return {
        "postgresql": {
            "enabled": pg,
            "auth": {"password": secret(PG_PASSWORD, "postgres", existing)},
            "external": {"host": "postgres.example.test"} if not pg else {},
        },
        "redis": {
            "enabled": redis,
            "auth": {"password": secret(REDIS_PASSWORD, "redis", existing)},
            "external": {"host": "redis.example.test"} if not redis else {},
        },
    }


def runtime_values(pg=True, redis=True, existing=False, ingress=False, rabbit=True):
    return infrastructure_values(pg, redis, existing) | {
        "application": {
            "server": {"publicOrigin": "https://runtime.example.test"},
            "security": {
                "controlPlaneApiKey": secret(CONTROL_KEY, "control-plane", existing)
            },
            "email": {
                "fromAddress": "runtime@example.test",
                "smtp": {"host": "smtp.example.test"},
            },
        },
        "rabbitmq": {
            "enabled": rabbit,
            "auth": {"password": secret(RABBIT_PASSWORD, "rabbitmq", existing)},
            "external": {"host": "rabbitmq.example.test"} if not rabbit else {},
        },
        "ingress": {
            "enabled": ingress,
            "className": "nginx" if ingress else "",
            "tls": {"secretName": "runtime-test-tls"} if ingress else {},
        },
    }


class UniqueKeyLoader(yaml.SafeLoader):
    """Ordinary YAML loading silently discards duplicate keys."""

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


def objects(text):
    return [item for item in yaml.load_all(text, Loader=UniqueKeyLoader) if item]


class HelmContractTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if shutil.which(HELM) is None:
            raise RuntimeError("Helm is required; set HELM to its executable path")

    def run_helm(
        self,
        chart,
        values,
        command="template",
        success=True,
        release="contract",
        upgrade=False,
    ):
        with tempfile.TemporaryDirectory(prefix="dnk-helm-render-") as directory:
            values_file = Path(directory) / "values.yaml"
            values_file.write_text(yaml.safe_dump(values))
            arguments = [HELM, command]
            if command == "template":
                arguments += [release]
                if upgrade:
                    arguments += ["--is-upgrade"]
            arguments += [str(chart), "-f", str(values_file)]
            if command == "lint":
                arguments += ["--strict"]
            result = subprocess.run(arguments, text=True, capture_output=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        else:
            self.assertNotEqual(
                result.returncode, 0, "invalid configuration unexpectedly rendered"
            )
        return result

    def render(self, values, chart=RUNTIME, **kwargs):
        return objects(self.run_helm(chart, values, **kwargs).stdout)

    def assert_contract(
        self,
        manifests,
        packages,
        pg=True,
        redis=True,
        existing=False,
        ingress=False,
        rabbit=True,
    ):
        self.assertFalse(
            any((r["metadata"]["name"].endswith("-gateway") for r in manifests))
        )
        counts = len(packages)
        deployments = [r for r in manifests if r["kind"] == "Deployment"]
        jobs = [r for r in manifests if r["kind"] == "Job"]
        self.assertEqual(len(deployments), 2 * counts + int("runtime" in packages))
        self.assertEqual(len(jobs), counts)
        statefulsets = [r for r in manifests if r["kind"] == "StatefulSet"]
        self.assertEqual(
            len(statefulsets),
            counts * (int(pg) + int(redis)) + int("runtime" in packages and rabbit),
        )
        identifiers = [(r["kind"], r["metadata"]["name"]) for r in manifests]
        self.assertEqual(
            len(identifiers), len(set(identifiers)), "resource names collide"
        )
        configs = {
            r["metadata"]["name"]: r for r in manifests if r["kind"] == "ConfigMap"
        }
        secrets = {r["metadata"]["name"]: r for r in manifests if r["kind"] == "Secret"}
        services = {
            r["metadata"]["name"]: r for r in manifests if r["kind"] == "Service"
        }
        public_text = yaml.safe_dump([r for r in manifests if r["kind"] != "Secret"])
        for value in [
            SECRET_KEY,
            FERNET_KEY,
            PG_PASSWORD,
            REDIS_PASSWORD,
            RABBIT_PASSWORD,
            CONTROL_KEY,
        ]:
            self.assertNotIn(
                value, public_text, "credential outside a Kubernetes Secret"
            )
        if existing:
            self.assertFalse(secrets, "existing secrets must not be recreated")

        def resolve_env(container):
            env = {}
            for source in container.get("envFrom", []):
                if "configMapRef" in source:
                    data = configs[source["configMapRef"]["name"]]["data"]
                    self.assertFalse(set(data) & set(env))
                    self.assertTrue(
                        all((isinstance(value, str) for value in data.values()))
                    )
                    env.update(data)
            for entry in container.get("env", []):
                self.assertNotIn(entry["name"], env, "duplicate environment variable")
                env[entry["name"]] = entry.get("value", entry.get("valueFrom"))
                ref = entry.get("valueFrom", {}).get("secretKeyRef")
                if ref:
                    if existing:
                        self.assertEqual(ref["name"], "test-secrets")
                    else:
                        self.assertIn(ref["name"], secrets)
                        self.assertIn(
                            ref["key"],
                            secrets[ref["name"]].get("data", {})
                            | secrets[ref["name"]].get("stringData", {}),
                        )
            return env

        job_names = {r["metadata"]["name"] for r in jobs}
        for job in jobs:
            annotations = job["metadata"]["annotations"]
            self.assertEqual(annotations["argocd.argoproj.io/hook"], "Sync")
            self.assertEqual(
                annotations["argocd.argoproj.io/hook-delete-policy"],
                "BeforeHookCreation",
            )
            self.assertEqual(annotations["argocd.argoproj.io/sync-wave"], "-10")
            self.assertIn("dnk.io/deployment-token", annotations)
            self.assertTrue(job["metadata"]["name"].endswith("-migrate-r1"))
            self.assertNotIn("ttlSecondsAfterFinished", job["spec"])
            self.assertNotIn("helm.sh/hook", annotations)
            self.assertFalse(podspec(job).get("automountServiceAccountToken", True))
            for container in podspec(job)["containers"]:
                resolve_env(container)
        roles = [r for r in manifests if r["kind"] == "Role"]
        self.assertEqual(len(roles), 1)
        self.assertEqual(
            roles[0]["rules"],
            [
                {
                    "apiGroups": ["batch"],
                    "resources": ["jobs"],
                    "resourceNames": sorted(job_names),
                    "verbs": ["get"],
                }
            ],
        )
        targets = [
            json.loads(c["data"]["targets.json"])
            for c in configs.values()
            if "targets.json" in c.get("data", {})
        ]
        self.assertEqual(len(targets), 1)
        self.assertEqual({t["name"] for t in targets[0]}, job_names)
        for target in targets[0]:
            job = next((j for j in jobs if j["metadata"]["name"] == target["name"]))
            self.assertEqual(
                target["token"],
                job["metadata"]["annotations"]["dnk.io/deployment-token"],
            )
        for deployment in deployments:
            spec = podspec(deployment)
            self.assertFalse(spec.get("automountServiceAccountToken", True))
            self.assertTrue(spec["serviceAccountName"])
            gate = spec["initContainers"]
            self.assertEqual(len(gate), 1)
            self.assertEqual(gate[0]["name"], "wait-migrations")
            token_volumes = {
                v["name"]
                for v in spec["volumes"]
                if any(
                    (
                        "serviceAccountToken" in s
                        for s in v.get("projected", {}).get("sources", [])
                    )
                )
            }
            self.assertEqual(len(token_volumes), 1)
            self.assertTrue(
                token_volumes <= {v["name"] for v in gate[0]["volumeMounts"]}
            )
            for container in spec["containers"]:
                self.assertFalse(
                    token_volumes
                    & {v["name"] for v in container.get("volumeMounts", [])}
                )
                env = resolve_env(container)
                if component(deployment) in {"backend", "frontend"}:
                    for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
                        self.assertIn(probe, container)
                if "CORE_PUBLIC_ORIGIN" in env:
                    self.assertEqual(
                        env["CORE_PUBLIC_ORIGIN"], "https://core.example.test"
                    )
                    self.assertEqual(env["CORE_SESSION_COOKIE_AGE"], "1209600")
                    self.assertEqual(env["CORE_DB_HOST"] in services, pg)
                    self.assertEqual(env["CORE_REDIS_HOST"] in services, redis)
                    self.assertIn("secretKeyRef", env["CORE_SECRET_KEY"])
                if "NUXT_PUBLIC_SITE_URL" in env:
                    self.assertEqual(
                        env["NUXT_PUBLIC_SITE_URL"], "https://core.example.test"
                    )
            annotations = deployment["spec"]["template"]["metadata"]["annotations"]
            self.assertTrue(any((key.startswith("checksum/") for key in annotations)))
        for statefulset in statefulsets:
            self.assertEqual(
                statefulset["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"],
                "-20",
            )
            self.assertTrue(statefulset["spec"]["volumeClaimTemplates"])
            self.assertEqual(
                statefulset["spec"]
                .get("persistentVolumeClaimRetentionPolicy", {})
                .get("whenDeleted", "Retain"),
                "Retain",
            )
            self.assertIn(statefulset["spec"]["serviceName"], services)
        for config in configs.values():
            self.assertEqual(
                config["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"], "-30"
            )
        ingresses = [r for r in manifests if r["kind"] == "Ingress"]
        self.assertEqual(len(ingresses), counts * int(ingress))
        for item in ingresses:
            self.assertEqual(
                item["spec"]["tls"][0]["hosts"], [item["spec"]["rules"][0]["host"]]
            )
            self.assertIn(
                item["spec"]["rules"][0]["http"]["paths"][0]["backend"]["service"][
                    "name"
                ],
                services,
            )

    def test_deployment_matrix(self):
        for pg, redis, existing, ingress in itertools.product([True, False], repeat=4):
            for chart, fixture, packages in [(RUNTIME, runtime_values, ["runtime"])]:
                with self.subTest(
                    chart=chart.name,
                    pg=pg,
                    redis=redis,
                    existing=existing,
                    ingress=ingress,
                ):
                    self.assert_contract(
                        self.render(
                            fixture(
                                pg=pg, redis=redis, existing=existing, ingress=ingress
                            ),
                            chart,
                        ),
                        packages,
                        pg,
                        redis,
                        existing,
                        ingress,
                    )

    def test_external_rabbitmq(self):
        self.assert_contract(
            self.render(runtime_values(rabbit=False), RUNTIME),
            ["runtime"],
            rabbit=False,
        )

    def test_default_published_images(self):
        for chart, values, expected in [(RUNTIME, runtime_values(), "runtime")]:
            manifests = self.render(values, chart)
            for deployment in (r for r in manifests if r["kind"] == "Deployment"):
                name = component(deployment)
                container = podspec(deployment)["containers"][0]
                suffix = "frontend-" + expected if name == "frontend" else expected
                self.assertEqual(
                    container["image"], "ghcr.io/dinikon/runtime/" + suffix + ":latest"
                )
                self.assertEqual(container["imagePullPolicy"], "Always")

    def test_direct_ingress_and_certificate_defaults(self):
        for chart, fixture, backend_paths in [(RUNTIME, runtime_values, {"/api"})]:
            values = fixture()
            del values["ingress"]
            values.setdefault("backend", {})["service"] = {"port": 8101}
            values.setdefault("frontend", {})["service"] = {"port": 3101}
            manifests = self.render(values, chart)
            ingress = next((r for r in manifests if r["kind"] == "Ingress"))
            fullname = ingress["metadata"]["name"]
            self.assertEqual(ingress["spec"]["ingressClassName"], "nginx")
            self.assertEqual(
                ingress["metadata"]["annotations"]["cert-manager.io/cluster-issuer"],
                "letsencrypt-production",
            )
            self.assertEqual(ingress["spec"]["tls"][0]["secretName"], fullname + "-tls")
            paths = ingress["spec"]["rules"][0]["http"]["paths"]
            self.assertEqual({p["path"] for p in paths}, backend_paths | {"/"})
            for path in paths:
                self.assertEqual(path["pathType"], "Prefix")
                backend = path["path"] in backend_paths
                self.assertEqual(
                    path["backend"]["service"],
                    {
                        "name": fullname + ("-backend" if backend else "-frontend"),
                        "port": {"number": 8101 if backend else 3101},
                    },
                )
            self.assertFalse(
                any((r["metadata"]["name"].endswith("-gateway") for r in manifests))
            )
            self.assertFalse(
                any(
                    (
                        r["kind"] == "Secret"
                        and r["metadata"]["name"] == fullname + "-tls"
                        for r in manifests
                    )
                )
            )

    def test_ingress_existing_certificate_and_invalid_settings(self):
        for chart, fixture in [(RUNTIME, runtime_values)]:
            values = fixture(ingress=True)
            values["ingress"]["tls"] = {
                "clusterIssuer": "",
                "secretName": "existing-tls",
            }
            ingress = next(
                (r for r in self.render(values, chart) if r["kind"] == "Ingress")
            )
            self.assertNotIn(
                "cert-manager.io/cluster-issuer", ingress["metadata"]["annotations"]
            )
            self.assertEqual(ingress["spec"]["tls"][0]["secretName"], "existing-tls")
            for override in [
                {"className": ""},
                {"tls": {"clusterIssuer": "Invalid Issuer"}},
                {"tls": {"secretName": "Invalid Secret"}},
                {"annotations": {"cert-manager.io/cluster-issuer": "conflicting"}},
                {"annotations": {"kubernetes.io/ingress.class": "conflicting"}},
                {"annotations": {"argocd.argoproj.io/sync-wave": "-50"}},
                {"annotations": {"invalid-type": True}},
            ]:
                invalid = fixture(ingress=True)
                invalid["ingress"].update(override)
                self.run_helm(chart, invalid, success=False)

    def test_lint_and_package_all_entrypoints(self):
        for chart, fixture in [(RUNTIME, runtime_values)]:
            with self.subTest(chart=chart.name):
                self.run_helm(chart, fixture(), command="lint")
                with tempfile.TemporaryDirectory(
                    prefix="dnk-helm-package-"
                ) as directory:
                    result = subprocess.run(
                        [HELM, "package", str(chart), "--destination", directory],
                        text=True,
                        capture_output=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.run_helm(next(Path(directory).glob("*.tgz")), fixture())

    def test_extra_env_and_disabled_migrations(self):
        for chart, fixture in [(RUNTIME, runtime_values)]:
            values = fixture()
            values["migrations"] = {"enabled": False}
            values["backend"] = {
                "extraEnv": [
                    {
                        "name": "CUSTOM",
                        "valueFrom": {
                            "secretKeyRef": {"name": "extra", "key": "token"}
                        },
                    }
                ]
            }
            manifests = self.render(values, chart)
            self.assertFalse(
                any(
                    (
                        r["kind"] in {"Job", "Role", "RoleBinding", "ServiceAccount"}
                        for r in manifests
                    )
                )
            )
            for deployment in (r for r in manifests if r["kind"] == "Deployment"):
                self.assertFalse(podspec(deployment).get("initContainers"))
            backend = next(
                (
                    r
                    for r in manifests
                    if r["kind"] == "Deployment" and component(r) == "backend"
                )
            )
            self.assertIn(
                values["backend"]["extraEnv"][0],
                podspec(backend)["containers"][0]["env"],
            )

    def test_secret_urls_and_existing_persistence(self):
        for chart, fixture in [(RUNTIME, runtime_values)]:
            values = fixture(redis=False)
            values["redis"]["auth"]["password"] = {"value": ""}
            values["redis"]["external"] = {
                "url": {"value": "rediss://test:p%40ss@redis.example.test:6380/2"}
            }
            if chart == RUNTIME:
                values["rabbitmq"]["enabled"] = False
                values["rabbitmq"]["auth"]["password"] = {"value": ""}
                values["rabbitmq"]["external"] = {
                    "url": {
                        "existingSecret": {"name": "amqp-credentials", "key": "url"}
                    }
                }
            manifests = self.render(values, chart)
            public = yaml.safe_dump([r for r in manifests if r["kind"] != "Secret"])
            self.assertNotIn("rediss://test:p%40ss", public)
            if chart == RUNTIME:
                self.assertIn("amqp-credentials", public)
            values = fixture()
            for dependency in ["postgresql", "redis"] + (
                ["rabbitmq"] if chart == RUNTIME else []
            ):
                values[dependency]["persistence"] = {
                    "existingClaim": dependency + "-existing"
                }
            for resource in self.render(values, chart):
                if resource["kind"] == "StatefulSet":
                    self.assertFalse(resource["spec"].get("volumeClaimTemplates"))
                    self.assertTrue(
                        any(
                            (
                                "persistentVolumeClaim" in v
                                for v in podspec(resource)["volumes"]
                            )
                        )
                    )

    def test_argocd_application_examples(self):
        examples = [
            item
            for path in (ROOT / "deploy/argocd").glob("*.yaml")
            for item in objects(path.read_text())
            if item["kind"] == "Application"
        ]
        self.assertEqual(len(examples), 2)
        for application in examples:
            self.assertEqual(application["apiVersion"], "argoproj.io/v1alpha1")
            spec = application["spec"]
            self.assertEqual(
                spec["source"]["repoURL"], "oci://ghcr.io/dinikon/dnk-runtime-core/helm"
            )
            self.assertEqual(spec["source"]["path"], ".")
            self.assertNotIn("chart", spec["source"])
            if application["metadata"]["name"].endswith("-dev"):
                self.assertEqual(spec["source"]["targetRevision"], "dev")
                self.assertTrue(spec["syncPolicy"]["automated"]["enabled"])
                self.assertNotIn("parameters", spec["source"]["helm"])
            else:
                self.assertTrue(spec["source"]["targetRevision"].startswith("sha256:"))
                self.assertNotIn("automated", spec["syncPolicy"])
                self.assertEqual(
                    spec["source"]["helm"]["parameters"][0]["name"],
                    "global.deployment.revision",
                )
            self.assertIn("CreateNamespace=true", spec["syncPolicy"]["syncOptions"])
            values = yaml.load(spec["source"]["helm"]["values"], Loader=UniqueKeyLoader)
            self.run_helm(RUNTIME, values)

    def test_invalid_configuration_rejected(self):
        for chart, fixture, reserved, key_path in [
            (
                RUNTIME,
                runtime_values,
                "DB_PASSWORD",
                ("application", "security", "controlPlaneApiKey"),
            )
        ]:
            cases = []
            for path in [
                ("application", "server", "publicOrigin"),
                (*key_path, "value"),
                ("backend", "image", "tag"),
                ("frontend", "image", "repository"),
                ("postgresql", "auth", "password", "value"),
                ("redis", "auth", "password", "value"),
            ]:
                values = fixture()
                section = values
                for key in path[:-1]:
                    section = section.setdefault(key, {})
                section[path[-1]] = ""
                cases.append(("missing " + ".".join(path), values))
            for origin in [
                "http://invalid.test",
                "https://invalid.test/path",
                "https://user:password@invalid.test",
                "https://invalid.test:70000",
            ]:
                values = fixture()
                values["application"]["server"]["publicOrigin"] = origin
                cases.append(("invalid origin " + origin, values))
            values = fixture()
            section = values
            for key in key_path:
                section = section[key]
            section["existingSecret"] = {"name": "duplicate", "key": "key"}
            cases.append(("conflicting secret sources", values))
            for env in [
                [{"name": reserved, "value": "bad"}],
                [{"name": "CUSTOM", "value": "a"}, {"name": "CUSTOM", "value": "b"}],
            ]:
                values = fixture()
                values["backend"] = {"extraEnv": env}
                cases.append(("conflicting environment", values))
            for service in ["postgresql", "redis"]:
                for invalid in [{"host": ""}, {"port": 70000}]:
                    values = fixture(
                        pg=service != "postgresql", redis=service != "redis"
                    )
                    values[service]["external"].update(invalid)
                    cases.append(("invalid external " + service, values))
            values = fixture(ingress=True)
            values["ingress"]["tls"] = {"secretName": "", "clusterIssuer": ""}
            cases.append(("missing TLS secret", values))
            for label, values in cases:
                with self.subTest(chart=chart.name, case=label):
                    self.run_helm(chart, values, success=False)


if __name__ == "__main__":
    unittest.main()
