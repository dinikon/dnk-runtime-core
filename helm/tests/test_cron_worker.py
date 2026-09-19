"""Helm contracts for the PostgreSQL-backed scheduled-jobs CronWorker."""

from test_render import HelmContractTests, RUNTIME, component, podspec, runtime_values


class CronWorkerDeploymentTests(HelmContractTests):
    def test_default_cron_worker_has_worker_only_contract(self):
        manifests = self.render(runtime_values(), RUNTIME)
        deployment = next(
            item
            for item in manifests
            if item["kind"] == "Deployment" and component(item) == "cron"
        )
        spec = podspec(deployment)
        container = spec["containers"][0]
        self.assertEqual(container["args"], ["dnk-manage", "jobs", "worker"])
        self.assertEqual(spec["terminationGracePeriodSeconds"], 60)
        self.assertEqual(
            container["readinessProbe"]["exec"]["command"],
            ["dnk-manage", "jobs", "healthcheck"],
        )
        env = {
            item["name"]: item["value"]
            for item in container["env"]
            if "value" in item
        }
        self.assertEqual(env["SCHEDULED_JOBS__POLL_INTERVAL_SECONDS"], "2")
        self.assertEqual(env["SCHEDULED_JOBS__LOCK_TTL_SECONDS"], "300")
        self.assertEqual(container["resources"]["limits"]["memory"], "1Gi")
        self.assertFalse(
            any(
                item["kind"] == "Service" and component(item) == "cron"
                for item in manifests
            )
        )

    def test_cron_worker_can_be_disabled(self):
        values = runtime_values()
        values["workers"] = {"cron": {"enabled": False}}
        manifests = self.render(values, RUNTIME)
        self.assertFalse(
            any(
                item["kind"] == "Deployment" and component(item) == "cron"
                for item in manifests
            )
        )
