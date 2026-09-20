from test_render import HelmContractTests, RUNTIME, runtime_values


class CurrencySyncTests(HelmContractTests):
    def test_disabled_by_default(self):
        manifests = self.render(runtime_values(), RUNTIME)
        self.assertFalse(any(item["kind"] == "CronJob" for item in manifests))

    def test_global_sync_is_a_separate_cronjob(self):
        values = runtime_values()
        values.setdefault("application", {})["currency"] = {
            "nbu": {"syncEnabled": True}
        }
        manifests = self.render(values, RUNTIME)
        job = next(item for item in manifests if item["kind"] == "CronJob")
        self.assertEqual(job["spec"]["concurrencyPolicy"], "Forbid")
        self.assertEqual(job["spec"]["timeZone"], "Etc/UTC")
        pod = job["spec"]["jobTemplate"]["spec"]["template"]["spec"]
        self.assertEqual(
            pod["containers"][0]["args"],
            ["dnk-manage", "currency", "sync-rates", "--scheduled"],
        )
