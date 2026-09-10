"""Optional delivery. No registry/Argo calls are made unless explicitly enabled."""

import json
import os
import time

from .artifacts import Registry
from .common import Error, run


class Argo:
    def __init__(self, app):
        self.app = app

    def call(self, command, *args):
        return run("argocd", "app", command, self.app, *args, "--grpc-web").stdout

    def get(self, refresh=False):
        return json.loads(
            self.call("get", "-o", "json", *(["--hard-refresh"] if refresh else []))
        )

    def wait_operation(self):
        self.call("wait", "--operation", "--timeout", "900")

    def select(self, digest, revision):
        self.call(
            "set",
            "--revision",
            digest,
            "--helm-set-string",
            "global.deployment.revision=" + revision,
        )

    def sync(self):
        self.call("sync", "--prune", "--timeout", "900")


def deliver(
    repo,
    record,
    github,
    enabled=None,
    registry=None,
    argo=None,
    run_id=None,
    attempt=None,
    timeout=900,
):
    enabled = os.environ.get("DEPLOY_ENABLED", "") if enabled is None else enabled
    if enabled != "true":
        print(
            "Deployment disabled: artifacts prepared; ArgoCD and the dev alias were not changed"
        )
        return False
    if record["channel"] not in ("dev", "stable"):
        raise Error("Prereleases are never deployed")
    if argo is None:
        for key in ("ARGOCD_SERVER", "ARGOCD_AUTH_TOKEN", "ARGOCD_APP"):
            if not os.environ.get(key):
                raise Error(f"Set {key} before enabling deployment")
        argo = Argo(os.environ["ARGOCD_APP"])
    registry = registry or Registry()
    branch, digest = record["branch"], record["chart_digest"]

    def current():
        repo.fetch()
        return repo.sha("origin/" + branch) == record["build_sha"]

    if not current():
        print("A newer branch HEAD exists; skipping this delivery")
        return False
    application = argo.get()
    source = application["spec"]["source"]
    if (
        source.get("repoURL") != "oci://" + record["chart_repository"]
        or source.get("path") != "."
        or "chart" in source
    ):
        raise Error(
            "Prepare this Application's native OCI source before enabling delivery"
        )
    automated = application["spec"].get("syncPolicy", {}).get("automated")
    auto_enabled = automated is not None and automated.get("enabled", True)
    if record["channel"] == "dev":
        if source.get("targetRevision") != "dev" or not auto_enabled:
            raise Error("Dev requires targetRevision dev and automated sync")
        if any(
            p["name"] == "global.deployment.revision"
            for p in source.get("helm", {}).get("parameters", [])
        ):
            raise Error(
                "Dev deployment revision must come from its package, not an Application override"
            )
    elif auto_enabled:
        raise Error("Disable production auto-sync before enabling explicit delivery")
    if application.get("operation") or (
        application.get("status", {}).get("operationState", {}).get("phase")
        == "Running"
    ):
        argo.wait_operation()
    if not current():
        return False
    if record["channel"] == "dev":
        registry.alias(record["chart_repository"], digest, "dev")
        refreshed = argo.get(refresh=True)
        previous = refreshed.get("status", {}).get("operationState", {})
        if (
            previous.get("phase") in ("Failed", "Error")
            and previous.get("syncResult", {}).get("revision") == digest
        ):
            # Auto-sync does not retry an already failed revision by itself.
            argo.sync()
    else:
        run_id = run_id or os.environ["GITHUB_RUN_ID"]
        attempt = attempt or os.environ["GITHUB_RUN_ATTEMPT"]
        argo.select(digest, f"prod-{record['build_sha']}-{run_id}-{attempt}")
        argo.get(refresh=True)
        argo.sync()
    deadline = time.monotonic() + timeout
    while True:
        application = argo.get()
        state = application["status"]
        operation = state.get("operationState", {})
        if (
            not application.get("operation")
            and state.get("sync", {}).get("revision") == digest
            and state["sync"].get("status") == "Synced"
            and state.get("health", {}).get("status") == "Healthy"
            and operation.get("phase") == "Succeeded"
            and operation.get("syncResult", {}).get("revision") == digest
        ):
            break
        if (
            operation.get("phase") in ("Failed", "Error")
            and operation.get("syncResult", {}).get("revision") == digest
        ):
            raise Error(
                "ArgoCD delivery failed: "
                + operation.get("message", "inspect the Application")
            )
        if time.monotonic() >= deadline:
            raise Error(
                "Timed out waiting for the selected digest and its migration/rollout"
            )
        time.sleep(5)
    if record["channel"] == "stable":
        github.finalize("v" + record["app_version"])
    print(f"Delivered {branch}: {digest}")
    return True
