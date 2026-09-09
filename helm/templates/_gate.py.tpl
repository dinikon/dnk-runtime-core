{{- define "dnk.lifecycle.gateScript" -}}
"""Wait for this deployment's migration Jobs using read-only Kubernetes access."""

import json
import os
from pathlib import Path
import ssl
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class MigrationFailure(RuntimeError):
    """A Job or API authorization failure prevents startup."""


def job_state(job, expected_token):
    """Return a pending reason or None; never trust a stale or deleting Job."""
    if job is None:
        return "not created"
    metadata = job.get("metadata", {})
    if metadata.get("deletionTimestamp"):
        return "being deleted"
    if metadata.get("annotations", {}).get("dnk.io/deployment-token") != expected_token:
        return "belongs to another deployment"
    conditions = job.get("status", {}).get("conditions", [])
    if any(c.get("type") == "Failed" and c.get("status") == "True" for c in conditions):
        raise MigrationFailure("migration Job failed; inspect its logs before redeploying")
    if any(c.get("type") == "Complete" and c.get("status") == "True" for c in conditions):
        return None
    return "still running"


class KubernetesJobs:
    def __init__(self, namespace):
        host = os.environ.get("KUBERNETES_SERVICE_HOST", "kubernetes.default.svc")
        if ":" in host and not host.startswith("["):
            host = "[" + host + "]"
        port = os.environ.get("KUBERNETES_SERVICE_PORT_HTTPS", "443")
        self.url = "https://{}:{}/apis/batch/v1/namespaces/{}/jobs/".format(
            host, port, quote(namespace, safe="")
        )
        self.context = ssl.create_default_context(cafile="/var/run/dnk-api/ca.crt")

    def get(self, name):
        # Read every request so projected-token rotation also works for long waits.
        token = Path("/var/run/dnk-api/token").read_text().strip()
        request = Request(
            self.url + quote(name, safe=""),
            headers={"Authorization": "Bearer " + token, "Accept": "application/json"},
        )
        try:
            with urlopen(request, context=self.context, timeout=10) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code == 404:
                return None
            if error.code in (401, 403):
                raise MigrationFailure("Kubernetes denied access to migration Job (HTTP {})".format(error.code)) from None
            if 400 <= error.code < 500 and error.code != 429:
                raise MigrationFailure("Kubernetes rejected migration Job lookup (HTTP {})".format(error.code)) from None
            raise ConnectionError("Kubernetes API temporarily unavailable") from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise ConnectionError("Kubernetes API temporarily unavailable") from None


def wait_for_jobs(targets, get_job, timeout, poll_interval=2, *, clock=time.monotonic, sleep=time.sleep, log=print):
    deadline = clock() + timeout
    last_message = None
    while True:
        pending = []
        for target in targets:
            name = target["name"]
            try:
                reason = job_state(get_job(name), target["token"])
            except MigrationFailure as error:
                raise MigrationFailure("{}: {}".format(name, error)) from None
            except ConnectionError:
                reason = "Kubernetes API temporarily unavailable"
            if reason:
                pending.append("{}: {}".format(name, reason))
        if not pending:
            log("All migration Jobs completed successfully.")
            return
        message = "; ".join(pending)
        if message != last_message:
            log("Waiting for migrations: " + message)
            last_message = message
        remaining = deadline - clock()
        if remaining <= 0:
            raise MigrationFailure("Timed out waiting for migrations: " + message)
        sleep(min(poll_interval, remaining))


def load_targets(expected_token, deadline, *, clock=time.monotonic, sleep=time.sleep):
    """Projected ConfigMaps can briefly lag the pod template during an upgrade."""
    token_path = Path("/opt/dnk-gate/deployment-token")
    while True:
        if token_path.read_text().strip() == expected_token:
            targets = json.loads(Path("/opt/dnk-gate/targets.json").read_text())
            # A projection update between reads must not mix deployment versions.
            if token_path.read_text().strip() == expected_token and all(
                target["token"] == expected_token for target in targets
            ):
                return targets
        remaining = deadline - clock()
        if remaining <= 0:
            raise MigrationFailure("Timed out waiting for this deployment's migration coordinator")
        sleep(min(2, remaining))


def main():
    deadline = time.monotonic() + float(os.environ.get("DNK_GATE_TIMEOUT_SECONDS", "900"))
    targets = load_targets(os.environ["DNK_GATE_DEPLOYMENT_TOKEN"], deadline)
    if not targets:
        print("No migration Jobs are enabled.", flush=True)
        return
    client = KubernetesJobs(os.environ["DNK_GATE_NAMESPACE"])
    wait_for_jobs(
        targets, client.get, max(0, deadline - time.monotonic()),
        log=lambda message: print(message, flush=True),
    )


if __name__ == "__main__":
    try:
        main()
    except MigrationFailure as error:
        print(str(error), file=sys.stderr, flush=True)
        sys.exit(1)
{{- end -}}
