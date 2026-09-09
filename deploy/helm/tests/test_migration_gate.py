"""Exercise the exact Python entrypoint embedded in the lifecycle library."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import types
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "deploy/helm/dnk-platform/charts/dnk-common/templates/_gate.py.tpl"
SOURCE = TEMPLATE.read_text().split("\n", 1)[1].rsplit("{{- end -}}", 1)[0]
GATE = types.ModuleType("migration_gate")
exec(compile(SOURCE, str(TEMPLATE), "exec"), GATE.__dict__)


def job(*, token="current", condition=None, status="True", deleting=False):
    document = {"metadata": {"annotations": {"dnk.io/deployment-token": token}}}
    if deleting:
        document["metadata"]["deletionTimestamp"] = "2026-09-09T00:00:00Z"
    if condition:
        document["status"] = {"conditions": [{"type": condition, "status": status}]}
    return document


class Clock:
    def __init__(self):
        self.now = 0

    def time(self):
        return self.now

    def sleep(self, amount):
        self.now += amount


class MigrationGateTests(unittest.TestCase):
    def wait(self, getter, *, targets=None, timeout=4):
        timer = Clock()
        messages = []
        GATE.wait_for_jobs(
            targets or [{"name": "control-plane-migrate-r1", "token": "current"}],
            getter,
            timeout,
            clock=timer.time,
            sleep=timer.sleep,
            log=messages.append,
        )
        return timer, messages

    def test_only_current_complete_job_passes(self):
        self.assertIsNone(GATE.job_state(job(condition="Complete"), "current"))
        for document in (
            None,
            {},
            job(),
            job(condition="Complete", status="False"),
            job(condition="Complete", token="stale"),
            job(condition="Complete", deleting=True),
        ):
            with self.subTest(document=document):
                self.assertIsNotNone(GATE.job_state(document, "current"))

    def test_failed_current_job_blocks_immediately(self):
        with self.assertRaisesRegex(
            GATE.MigrationFailure, "control-plane-migrate-r1: migration Job failed"
        ):
            self.wait(lambda name: job(condition="Failed"))

    def test_stale_failed_and_deleting_jobs_wait_for_replacement(self):
        for document in (
            job(condition="Failed", token="stale"),
            job(condition="Failed", deleting=True),
        ):
            with self.subTest(document=document):
                self.assertIsNotNone(GATE.job_state(document, "current"))

    def test_failure_takes_precedence_over_contradictory_complete(self):
        document = job(condition="Complete")
        document["status"]["conditions"].append({"type": "Failed", "status": "True"})
        with self.assertRaises(GATE.MigrationFailure):
            GATE.job_state(document, "current")

    def test_missing_then_stale_then_current_complete(self):
        documents = iter(
            [None, job(token="old", condition="Complete"), job(condition="Complete")]
        )
        timer, messages = self.wait(lambda name: next(documents), timeout=10)
        self.assertEqual(timer.now, 4)
        self.assertIn("not created", messages[0])
        self.assertIn("another deployment", messages[1])
        self.assertIn("successfully", messages[-1])

    def test_shared_barrier_waits_for_both_and_rechecks_completion(self):
        calls = []

        def lookup(name):
            calls.append(name)
            if name == "runtime" and calls.count(name) < 3:
                return job()
            return job(condition="Complete")

        timer, messages = self.wait(
            lookup,
            targets=[
                {"name": "control-plane", "token": "current"},
                {"name": "runtime", "token": "current"},
            ],
            timeout=10,
        )
        self.assertEqual(timer.now, 4)
        self.assertEqual(calls, ["control-plane", "runtime"] * 3)
        self.assertEqual(
            len(messages), 2, "Repeated unchanged states should not flood logs"
        )

    def test_shared_barrier_does_not_cache_disappeared_job(self):
        counts = {"control-plane": 0, "runtime": 0}

        def lookup(name):
            counts[name] += 1
            if name == "control-plane":
                return job(condition="Complete") if counts[name] == 1 else None
            return job() if counts[name] == 1 else job(condition="Complete")

        with self.assertRaisesRegex(
            GATE.MigrationFailure, "control-plane: not created"
        ):
            self.wait(
                lookup,
                targets=[
                    {"name": "control-plane", "token": "current"},
                    {"name": "runtime", "token": "current"},
                ],
            )

    def test_timeout_reports_missing_or_wrong_deployment(self):
        for document, message in (
            (None, "not created"),
            (job(token="stale", condition="Complete"), "another deployment"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(
                    GATE.MigrationFailure, "Timed out.*" + message
                ):
                    self.wait(lambda name: document)

    def test_temporary_api_failure_recovers_without_secret_logging(self):
        attempts = 0

        def lookup(name):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise ConnectionError("sensitive server diagnostics")
            return job(condition="Complete")

        _, messages = self.wait(lookup)
        self.assertIn("API temporarily unavailable", messages[0])
        self.assertNotIn("sensitive", " ".join(messages))

    def test_empty_targets_are_successful_without_api_calls(self):
        def unexpected(name):
            self.fail("No lookup is needed for an empty barrier")

        GATE.wait_for_jobs([], unexpected, 0, log=lambda message: None)

    def test_stale_coordinator_projection_does_not_trust_old_success(self):
        timer = Clock()
        targets = [{"name": "current-job", "token": "current"}]
        with patch.object(
            GATE.Path,
            "read_text",
            side_effect=["old", "current", json.dumps(targets), "current"],
        ):
            result = GATE.load_targets(
                "current", 10, clock=timer.time, sleep=timer.sleep
            )
        self.assertEqual(result, targets)
        self.assertEqual(timer.now, 2)

    def test_projection_update_between_reads_cannot_mix_tokens(self):
        timer = Clock()
        targets = [{"name": "current-job", "token": "current"}]
        values = [
            "current",
            json.dumps(targets),
            "old",
            "current",
            json.dumps(targets),
            "current",
        ]
        with patch.object(GATE.Path, "read_text", side_effect=values):
            result = GATE.load_targets(
                "current", 10, clock=timer.time, sleep=timer.sleep
            )
        self.assertEqual(result, targets)
        self.assertEqual(timer.now, 2)

    def test_stale_coordinator_times_out_including_empty_old_targets(self):
        timer = Clock()
        with patch.object(GATE.Path, "read_text", return_value="old"):
            with self.assertRaisesRegex(GATE.MigrationFailure, "migration coordinator"):
                GATE.load_targets("current", 4, clock=timer.time, sleep=timer.sleep)
        self.assertEqual(timer.now, 4)


class KubernetesTransportTests(unittest.TestCase):
    def setUp(self):
        self.ca_patch = patch.object(GATE.ssl, "create_default_context")
        self.ca = self.ca_patch.start()
        self.addCleanup(self.ca_patch.stop)
        self.token_patch = patch.object(
            GATE.Path, "read_text", return_value="token-secret"
        )
        self.token = self.token_patch.start()
        self.addCleanup(self.token_patch.stop)
        self.env_patch = patch.dict(
            GATE.os.environ,
            {
                "KUBERNETES_SERVICE_HOST": "kubernetes.default.svc",
                "KUBERNETES_SERVICE_PORT_HTTPS": "443",
            },
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.client = GATE.KubernetesJobs("workload-namespace")

    def test_uses_verified_https_and_reloads_rotated_projected_token(self):
        responses = [
            io.BytesIO(json.dumps(job(condition="Complete")).encode()) for _ in range(2)
        ]
        self.token.side_effect = ["first-token", "rotated-token"]
        with patch.object(GATE, "urlopen", side_effect=responses) as transport:
            self.client.get("migration-job")
            self.client.get("migration-job")
        self.ca.assert_called_once_with(cafile="/var/run/dnk-api/ca.crt")
        self.assertEqual(
            transport.call_args_list[0].args[0].get_header("Authorization"),
            "Bearer first-token",
        )
        self.assertEqual(
            transport.call_args_list[1].args[0].get_header("Authorization"),
            "Bearer rotated-token",
        )
        self.assertEqual(transport.call_args.kwargs["context"], self.ca.return_value)
        self.assertEqual(
            transport.call_args.args[0].full_url,
            "https://kubernetes.default.svc:443/apis/batch/v1/namespaces/workload-namespace/jobs/migration-job",
        )

    def test_ipv6_api_address(self):
        with patch.dict(GATE.os.environ, {"KUBERNETES_SERVICE_HOST": "fd00::1"}):
            self.assertTrue(
                GATE.KubernetesJobs("example").url.startswith("https://[fd00::1]:443/")
            )

    def test_missing_job_404_is_pending(self):
        with patch.object(
            GATE,
            "urlopen",
            side_effect=HTTPError(self.client.url, 404, "missing", None, None),
        ):
            self.assertIsNone(self.client.get("missing-job"))

    def test_api_denial_fails_without_exposing_response_body(self):
        for status in (401, 403, 400):
            with self.subTest(status=status):
                error = HTTPError(
                    self.client.url, status, "password-secret", None, None
                )
                with patch.object(GATE, "urlopen", side_effect=error):
                    with self.assertRaises(GATE.MigrationFailure) as raised:
                        self.client.get("job")
                self.assertIn(str(status), str(raised.exception))
                self.assertNotIn("secret", str(raised.exception))

    def test_network_errors_and_server_errors_are_retryable(self):
        for error in (
            HTTPError(self.client.url, 500, "secret", None, None),
            HTTPError(self.client.url, 429, "secret", None, None),
            URLError("secret"),
            TimeoutError("secret"),
        ):
            with self.subTest(error=type(error).__name__):
                with patch.object(GATE, "urlopen", side_effect=error):
                    with self.assertRaisesRegex(
                        ConnectionError, "API temporarily unavailable"
                    ) as raised:
                        self.client.get("job")
                self.assertNotIn("secret", str(raised.exception))

    def test_main_skips_api_when_no_migrations_are_enabled(self):
        output = io.StringIO()
        with (
            patch.object(
                GATE.Path, "read_text", side_effect=["current", "[]", "current"]
            ),
            patch.object(GATE, "KubernetesJobs") as client,
            patch.dict(GATE.os.environ, {"DNK_GATE_DEPLOYMENT_TOKEN": "current"}),
        ):
            with redirect_stdout(output):
                GATE.main()
        client.assert_not_called()
        self.assertIn("No migration Jobs", output.getvalue())


if __name__ == "__main__":
    unittest.main()
