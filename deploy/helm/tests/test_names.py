"""Reject overrides that would merge application or database resources."""

import unittest

import test_render as contracts


class ResourceNameTests(unittest.TestCase):
    def setUp(self):
        self.helm = contracts.HelmContractTests()

    def reject(self, values, chart=contracts.UMBRELLA):
        result = self.helm.run_helm(chart, values, success=False)
        self.assertIn("resource name collision", result.stderr + result.stdout)

    def test_app_collision_rejected_when_migrations_disabled(self):
        values = contracts.platform_values()
        for alias in ("controlPlane", "runtime"):
            values[alias].update(fullnameOverride="same", migrations={"enabled": False})
        self.reject(values)

    def test_embedded_postgresql_collision_rejected_across_packages(self):
        values = contracts.platform_values()
        for alias in ("controlPlane", "runtime"):
            values[alias]["postgresql"]["fullnameOverride"] = "shared-postgresql"
        self.reject(values)

    def test_managed_certificates_cannot_overwrite_each_others_secret(self):
        values = contracts.platform_values(ingress=True)
        for alias in ("controlPlane", "runtime"):
            values[alias]["ingress"]["tls"]["secretName"] = "shared-certificate"
        self.reject(values)
        # A manually managed wildcard certificate can be shared deliberately.
        for alias in ("controlPlane", "runtime"):
            values[alias]["ingress"]["tls"]["clusterIssuer"] = ""
        self.helm.render(values, chart=contracts.UMBRELLA)

    def test_standalone_dependency_cannot_shadow_application_service(self):
        values = contracts.core_values()
        values["migrations"] = {"enabled": False}
        values["postgresql"]["fullnameOverride"] = "contract-dnk-control-plane-backend"
        self.reject(values, chart=contracts.CORE)

    def test_standalone_dependencies_cannot_share_primary_service_name(self):
        values = contracts.runtime_values()
        values["redis"]["fullnameOverride"] = "shared-service"
        values["rabbitmq"]["fullnameOverride"] = "shared-service"
        self.reject(values, chart=contracts.RUNTIME)

    def test_primary_service_cannot_shadow_another_headless_service(self):
        values = contracts.core_values()
        values["postgresql"]["fullnameOverride"] = "database"
        values["redis"]["fullnameOverride"] = "database-pg-headless"
        self.reject(values, chart=contracts.CORE)

    def test_unique_names_do_not_allow_overlapping_database_selectors(self):
        values = contracts.platform_values()
        for alias in ("controlPlane", "runtime"):
            values[alias]["postgresql"]["nameOverride"] = "database"
            values[alias]["postgresql"]["fullnameOverride"] = (
                alias.lower() + "-postgres"
            )
        self.reject(values)

    def test_explicit_shared_external_database_is_valid(self):
        values = contracts.platform_values(pg=False)
        for alias in ("controlPlane", "runtime"):
            values[alias]["postgresql"]["external"]["host"] = "shared.example.test"
        self.helm.render(values, chart=contracts.UMBRELLA)

    def test_long_release_preserves_resource_names_and_references(self):
        resources = self.helm.render(
            contracts.platform_values(), chart=contracts.UMBRELLA, release="a" * 53
        )
        names = [(item["kind"], item["metadata"]["name"]) for item in resources]
        self.assertEqual(len(names), len(set(names)))
        for kind, name in names:
            self.assertLessEqual(len(name), 63, (kind, name))
        services = {name for kind, name in names if kind == "Service"}
        for item in resources:
            if item["kind"] == "StatefulSet":
                self.assertIn(item["spec"]["serviceName"], services)
            if item["kind"] == "ConfigMap" and "DB_HOST" in item.get("data", {}):
                self.assertIn(item["data"]["DB_HOST"], services)
            if item["kind"] == "ConfigMap" and "CORE_DB_HOST" in item.get("data", {}):
                self.assertIn(item["data"]["CORE_DB_HOST"], services)

    def test_empty_name_overrides_preserve_canonical_names_under_aliases(self):
        values = contracts.platform_values()
        values["controlPlane"]["nameOverride"] = ""
        values["runtime"]["nameOverride"] = ""
        umbrella = self.helm.render(values, chart=contracts.UMBRELLA)
        deployments = {
            item["metadata"]["name"]
            for item in umbrella
            if item["kind"] == "Deployment"
        }
        for alias, chart, canonical in (
            ("controlPlane", contracts.CORE, "dnk-control-plane"),
            ("runtime", contracts.RUNTIME, "dnk-runtime-core"),
        ):
            standalone = self.helm.render(values[alias], chart=chart)
            standalone_deployments = {
                item["metadata"]["name"]
                for item in standalone
                if item["kind"] == "Deployment"
            }
            self.assertIn("contract-" + canonical + "-backend", deployments)
            self.assertTrue(standalone_deployments.issubset(deployments))
        for resource in umbrella:
            self.assertRegex(
                resource["metadata"]["name"], r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$"
            )


if __name__ == "__main__":
    unittest.main()
