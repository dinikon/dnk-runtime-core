"""Standalone resource-name isolation contracts."""

import unittest
from test_render import HelmContractTests, RUNTIME, runtime_values


class NamesTest(unittest.TestCase):
    def test_dependencies_cannot_share_primary_service(self):
        values = runtime_values()
        for key in ["redis", "rabbitmq"]:
            values[key]["fullnameOverride"] = "shared-service"
        result = HelmContractTests().run_helm(RUNTIME, values, success=False)
        self.assertIn("resource name collision", result.stderr + result.stdout)

    def test_long_release_preserves_references(self):
        resources = HelmContractTests().render(
            runtime_values(), RUNTIME, release="a" * 53
        )
        identities = [(r["kind"], r["metadata"]["name"]) for r in resources]
        self.assertEqual(len(identities), len(set(identities)))
        services = {name for kind, name in identities if kind == "Service"}
        for resource in resources:
            if resource["kind"] == "StatefulSet":
                self.assertIn(resource["spec"]["serviceName"], services)
