"""Контракты внутреннего MinIO, общей конфигурации Runtime и хранения данных."""

import copy
from typing import Any
import unittest

import yaml

import test_render as render_support
from test_control_plane_deployment import integrated_values
from test_render import RUNTIME, component, podspec, runtime_values

ACCESS_KEY = "runtime-minio-render-user"
SECRET_KEY = "runtime-minio-render-secret"


def minio_values(existing: bool = False) -> dict[str, Any]:
    """Собирает независимые тестовые credentials для внутреннего хранилища."""
    values = runtime_values(existing=existing)
    values["minio"] = {
        "enabled": True,
        "auth": {
            name: (
                {"existingSecret": {"name": "minio-credentials", "key": key}}
                if existing
                else {"value": value}
            )
            for name, key, value in (
                ("accessKey", "access-key", ACCESS_KEY),
                ("secretKey", "secret-key", SECRET_KEY),
            )
        },
    }
    return values


class MinioDeploymentTests(unittest.TestCase):
    """Проверяет установку MinIO и подключение HTTP, cron и lifecycle процессов."""

    def setUp(self) -> None:
        """Использует существующий renderer с проверкой уникальности YAML-ключей."""
        self.renderer = render_support.HelmContractTests()

    def test_internal_storage_shares_endpoint_and_secret_refs_with_all_workers(
        self,
    ) -> None:
        """API, cron, publisher и lifecycle получают credentials самого MinIO."""
        for existing in (False, True):
            with self.subTest(existing=existing):
                values = integrated_values()
                values["minio"] = minio_values(existing)["minio"]
                manifests = self.renderer.render(values)
                statefulset = next(
                    item
                    for item in manifests
                    if item["kind"] == "StatefulSet" and component(item) == "minio"
                )
                service = next(
                    item
                    for item in manifests
                    if item["kind"] == "Service"
                    and item["metadata"]["name"] == statefulset["metadata"]["name"]
                )
                self.assertEqual(service["spec"]["type"], "ClusterIP")
                self.assertEqual(service["spec"]["ports"][0]["port"], 9000)
                container = podspec(statefulset)["containers"][0]
                credentials = {
                    entry["name"]: entry["valueFrom"]["secretKeyRef"]
                    for entry in container["env"]
                    if "valueFrom" in entry
                }
                self.assertEqual(
                    container["image"],
                    "quay.io/thanos/minio:RELEASE.2025-09-07T16-13-09Z",
                )
                self.assertFalse(podspec(statefulset).get("initContainers"))
                configs = {
                    item["metadata"]["name"]: item["data"]
                    for item in manifests
                    if item["kind"] == "ConfigMap"
                }
                for deployment in manifests:
                    if (
                        deployment["kind"] != "Deployment"
                        or component(deployment) == "frontend"
                    ):
                        continue
                    process = podspec(deployment)["containers"][0]
                    settings = configs[process["envFrom"][0]["configMapRef"]["name"]]
                    self.assertEqual(
                        settings["FILES__ENDPOINT"],
                        service["metadata"]["name"] + ":9000",
                    )
                    self.assertEqual(settings["FILES__SECURE"], "false")
                    env = {entry["name"]: entry for entry in process["env"]}
                    self.assertEqual(
                        env["FILES__ACCESS_KEY"]["valueFrom"]["secretKeyRef"],
                        credentials["MINIO_ROOT_USER"],
                    )
                    self.assertEqual(
                        env["FILES__SECRET_KEY"]["valueFrom"]["secretKeyRef"],
                        credentials["MINIO_ROOT_PASSWORD"],
                    )
                public = yaml.safe_dump(
                    [item for item in manifests if item["kind"] != "Secret"]
                )
                self.assertNotIn(ACCESS_KEY, public)
                self.assertNotIn(SECRET_KEY, public)
                auth_name = statefulset["metadata"]["name"] + "-auth"
                self.assertEqual(
                    any(
                        item["kind"] == "Secret"
                        and item["metadata"]["name"] == auth_name
                        for item in manifests
                    ),
                    not existing,
                )

    def test_storage_is_persistent_and_ingress_is_limited_to_this_release(self) -> None:
        """PVC сохраняется, S3 доступен pod того же релиза без публичного ingress."""
        manifests = self.renderer.render(minio_values())
        store = next(
            item
            for item in manifests
            if item["kind"] == "StatefulSet" and component(item) == "minio"
        )
        self.assertEqual(
            store["spec"]["volumeClaimTemplates"][0]["spec"]["resources"]["requests"][
                "storage"
            ],
            "20Gi",
        )
        self.assertNotIn("persistentVolumeClaimRetentionPolicy", store["spec"])
        self.assertFalse(podspec(store)["automountServiceAccountToken"])
        self.assertTrue(podspec(store)["securityContext"]["runAsNonRoot"])
        container = podspec(store)["containers"][0]
        self.assertTrue(container["securityContext"]["readOnlyRootFilesystem"])
        self.assertEqual(
            container["readinessProbe"]["httpGet"]["path"], "/minio/health/ready"
        )
        policy = next(
            item
            for item in manifests
            if item["kind"] == "NetworkPolicy" and component(item) == "minio"
        )
        peer = policy["spec"]["ingress"][0]["from"][0]
        self.assertNotIn("namespaceSelector", peer)
        self.assertEqual(
            peer["podSelector"]["matchLabels"],
            {
                "app.kubernetes.io/name": "dnk-runtime-core",
                "app.kubernetes.io/instance": "contract",
            },
        )
        self.assertEqual(
            policy["spec"]["ingress"][0]["ports"], [{"protocol": "TCP", "port": 9000}]
        )
        self.assertFalse(
            any(
                item["kind"] == "Ingress" and component(item) == "minio"
                for item in manifests
            )
        )

    def test_existing_volume_and_long_names_keep_service_references_valid(self) -> None:
        """Существующий PVC переиспользуется, длинное имя совпадает с FILES endpoint."""
        values = minio_values(existing=True)
        values["minio"]["persistence"] = {"existingClaim": "retained-minio-data"}
        manifests = self.renderer.render(values, release="a" * 53)
        store = next(
            item
            for item in manifests
            if item["kind"] == "StatefulSet" and component(item) == "minio"
        )
        self.assertNotIn("volumeClaimTemplates", store["spec"])
        self.assertIn(
            {
                "name": "data",
                "persistentVolumeClaim": {"claimName": "retained-minio-data"},
            },
            podspec(store)["volumes"],
        )
        services = {
            item["metadata"]["name"] for item in manifests if item["kind"] == "Service"
        }
        self.assertIn(store["spec"]["serviceName"], services)
        config = next(
            item["data"]
            for item in manifests
            if item["kind"] == "ConfigMap" and "FILES__ENDPOINT" in item.get("data", {})
        )
        self.assertIn(config["FILES__ENDPOINT"].removesuffix(":9000"), services)

    def test_external_storage_is_unchanged_when_internal_minio_is_disabled(
        self,
    ) -> None:
        """Внешний S3 endpoint и его независимые Secret references сохраняются."""
        values = runtime_values()
        values["application"]["files"] = {
            "endpoint": "private-s3.example.test:443",
            "secure": True,
            "accessKey": {"existingSecret": {"name": "external-minio", "key": "user"}},
            "secretKey": {
                "existingSecret": {"name": "external-minio", "key": "password"}
            },
        }
        manifests = self.renderer.render(values)
        self.assertFalse(any(component(item) == "minio" for item in manifests))
        config = next(
            item["data"]
            for item in manifests
            if item["kind"] == "ConfigMap" and "FILES__ENDPOINT" in item.get("data", {})
        )
        self.assertEqual(config["FILES__ENDPOINT"], "private-s3.example.test:443")
        self.assertEqual(config["FILES__SECURE"], "true")

    def test_missing_conflicting_and_short_credentials_fail_before_install(
        self,
    ) -> None:
        """Неполные credentials и две конкурирующие конфигурации отвергаются Helm."""
        changes = [
            {"minio": {"enabled": True}},
            {"application": {"files": {"endpoint": "external.example.test:9000"}}},
            {"application": {"files": {"accessKey": {"value": "other-user"}}}},
            {"minio": {"auth": {"secretKey": {"value": "short"}}}},
            {
                "minio": {
                    "auth": {
                        "accessKey": {
                            "value": ACCESS_KEY,
                            "existingSecret": {"name": "duplicate", "key": "user"},
                        }
                    }
                }
            },
        ]
        for index, change in enumerate(changes):
            with self.subTest(change=index):
                values = minio_values()
                if index == 0:
                    values["minio"] = change["minio"]
                elif "application" in change:
                    values["application"].update(change["application"])
                else:
                    for name, credential in change["minio"]["auth"].items():
                        values["minio"]["auth"][name] = credential
                self.renderer.run_helm(RUNTIME, values, success=False)

    def test_minio_resource_collisions_are_rejected(self) -> None:
        """MinIO не может занять имя Service другой инфраструктурной зависимости."""
        values = minio_values()
        values["minio"]["fullnameOverride"] = "shared-storage"
        values["redis"]["fullnameOverride"] = "shared-storage"
        result = self.renderer.run_helm(RUNTIME, values, success=False)
        self.assertIn("resource name collision", result.stderr)

    def test_standalone_subchart_is_installable_and_strictly_linted(self) -> None:
        """Локальный пакет MinIO работает самостоятельно и проходит строгий lint."""
        values = copy.deepcopy(minio_values()["minio"])
        self.renderer.run_helm(RUNTIME / "charts/minio", values, command="lint")
        self.renderer.run_helm(RUNTIME, minio_values(), command="lint")
