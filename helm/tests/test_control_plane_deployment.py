"""Real Helm-rendered isolation and credentials contracts for Runtime v1."""

import json

from test_render import HelmContractTests, RUNTIME, component, podspec, runtime_values


def integrated_values():
    values = runtime_values(ingress=True)
    values["ingress"]["hosts"] = ["*.first.example.test", "*.second.example.test"]
    values["controlPlane"] = {
        "enabled": True,
        "publicOrigin": "https://core.example.test",
        "managementOrigin": "https://core-management.example.test",
        "managementHost": "runtime-management.example.test",
        "allowedBaseDomains": ["first.example.test", "second.example.test"],
        "instanceId": "c50b45a1-acdc-4214-8a64-3fd8fbf8b101",
        "trustedProxyNetworks": ["10.10.0.0/24"],
        "allowedCoreFingerprints": ["a" * 64, "b" * 64],
        "ingressProbeAddress": "ingress.example.test:443",
        "credentialsSecret": "runtime-integration-credentials",
        "clientCaSecret": "core-client-ca",
        "rabbitmqUrl": {
            "existingSecret": {"name": "runtime-broker", "key": "provisioning-url"}
        },
    }
    return values


class ControlPlaneDeploymentTests(HelmContractTests):
    def test_management_is_isolated_and_worker_has_persistent_secret_references(self):
        manifests = self.render(integrated_values(), RUNTIME)
        management = next(
            r
            for r in manifests
            if r["kind"] == "Ingress" and r["metadata"]["name"].endswith("-management")
        )
        annotations = management["metadata"]["annotations"]
        self.assertEqual(
            annotations["nginx.ingress.kubernetes.io/auth-tls-verify-client"], "on"
        )
        self.assertEqual(
            annotations[
                "nginx.ingress.kubernetes.io/auth-tls-pass-certificate-to-upstream"
            ],
            "true",
        )
        self.assertEqual(
            management["spec"]["rules"][0]["host"], "runtime-management.example.test"
        )
        self.assertEqual(
            [p["path"] for p in management["spec"]["rules"][0]["http"]["paths"]],
            ["/internal/v1/"],
        )
        public = next(
            r
            for r in manifests
            if r["kind"] == "Ingress"
            and not r["metadata"]["name"].endswith("-management")
        )
        for rule in public["spec"]["rules"]:
            self.assertNotIn(
                "/internal/v1/", [p["path"] for p in rule["http"]["paths"]]
            )
        policies = [r for r in manifests if r["kind"] == "NetworkPolicy"]
        self.assertEqual(len(policies), 2)
        for policy in policies:
            allowed = policy["spec"]["ingress"][0]["from"]
            self.assertEqual(len(allowed), 1)
            self.assertIn("namespaceSelector", allowed[0])
            self.assertIn("podSelector", allowed[0])
        for name in ("backend", "lifecycle"):
            deployment = next(
                r
                for r in manifests
                if r["kind"] == "Deployment" and component(r) == name
            )
            container = podspec(deployment)["containers"][0]
            if name == "backend":
                self.assertIn("--no-proxy-headers", container["args"])
                self.assertNotIn("--forwarded-allow-ips", container["args"])
            else:
                self.assertEqual(
                    container["args"],
                    ["python", "-m", "src.modules.control_plane.worker"],
                )
                self.assertIn(
                    "--healthcheck", container["readinessProbe"]["exec"]["command"]
                )
            self.assertTrue(
                any(
                    v.get("secret", {}).get("secretName")
                    == "runtime-integration-credentials"
                    for v in podspec(deployment)["volumes"]
                )
            )
        config = next(
            r
            for r in manifests
            if r["kind"] == "ConfigMap"
            and r["metadata"]["name"].endswith("-config")
            and not r["metadata"]["name"].endswith("-migration-config")
        )
        self.assertEqual(
            len(json.loads(config["data"]["CONTROL_PLANE__ALLOWED_BASE_DOMAINS"])), 2
        )
        self.assertNotIn("CONTROL_PLANE_API_KEY", config["data"])
        migration = next(
            r
            for r in manifests
            if r["kind"] == "ConfigMap"
            and r["metadata"]["name"].endswith("-migration-config")
        )
        self.assertEqual(migration["data"]["CONTROL_PLANE__ENABLED"], "false")
        self.assertNotIn("CONTROL_PLANE__ENCRYPTION_KEY_PATH", migration["data"])

    def test_incomplete_trust_or_routing_cannot_enable_integration(self):
        for field, value in [
            ("credentialsSecret", ""),
            ("allowedCoreFingerprints", []),
            ("trustedProxyNetworks", ["0.0.0.0/0"]),
            ("allowedBaseDomains", ["unrouted.example.test"]),
        ]:
            with self.subTest(field=field):
                values = integrated_values()
                values["controlPlane"][field] = value
                self.run_helm(RUNTIME, values, success=False)
