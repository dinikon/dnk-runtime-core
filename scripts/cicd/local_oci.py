"""OCI/Argo integration in a NEW local Kind cluster only; no existing kubeconfig."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import uuid

from .artifacts import HELM_CONFIG, HELM_LAYER, Registry, package_chart
from .common import ROOT, run

# Existing cluster helper always creates its own kubeconfig and explicit context.
sys.path.insert(0, str(ROOT / "helm/tests"))
from cluster import Cluster, eventually  # noqa: E402

ARGO_VERSION = "v3.1.0"


def integration():
    registry = Registry(plain_http=True)
    name = "dnk-oci-" + uuid.uuid4().hex[:8]
    with Cluster(namespace="argo-platform", reuse_test_images=True) as cluster:
        try:
            run(
                "docker",
                "run",
                "-d",
                "--name",
                name,
                "--network",
                "kind",
                "--publish",
                "127.0.0.1::5000",
                "registry:2",
            )
            port = (
                run("docker", "port", name, "5000/tcp").stdout.strip().rsplit(":", 1)[1]
            )
            address = run(
                "docker",
                "inspect",
                "--format",
                '{{(index .NetworkSettings.Networks "kind").IPAddress}}',
                name,
            ).stdout.strip()
            repository = f"localhost:{port}/dnk-runtime-core/helm"
            internal = f"oci://{address}:5000/dnk-runtime-core/helm"
            cluster.kubectl("create", "namespace", "argocd")
            cluster.kubectl(
                "apply",
                "--server-side",
                "-f",
                f"https://raw.githubusercontent.com/argoproj/argo-cd/{ARGO_VERSION}/manifests/core-install.yaml",
                namespace="argocd",
            )
            cluster.kubectl(
                "wait",
                "--for=condition=Established",
                "--timeout=90s",
                "crd/applications.argoproj.io",
                "crd/appprojects.argoproj.io",
            )
            # Core install has no API server to generate this signing key.
            cluster.kubectl(
                "patch",
                "secret",
                "argocd-secret",
                "--type=merge",
                "-p",
                json.dumps({"stringData": {"server.secretkey": uuid.uuid4().hex}}),
                namespace="argocd",
            )
            cluster.apply(
                "oci-repository",
                [
                    {
                        "apiVersion": "v1",
                        "kind": "Secret",
                        "metadata": {
                            "name": "local-oci",
                            "labels": {"argocd.argoproj.io/secret-type": "repository"},
                        },
                        "stringData": {
                            "type": "oci",
                            "url": internal,
                            "insecureOCIForceHttp": "true",
                        },
                    },
                    {
                        "apiVersion": "argoproj.io/v1alpha1",
                        "kind": "AppProject",
                        "metadata": {"name": "local-oci"},
                        "spec": {
                            "sourceRepos": [internal],
                            "destinations": [
                                {
                                    "server": "https://kubernetes.default.svc",
                                    "namespace": cluster.namespace,
                                }
                            ],
                            "clusterResourceWhitelist": [
                                {"group": "", "kind": "Namespace"}
                            ],
                        },
                    },
                ],
                namespace="argocd",
            )
            for resource in (
                "deployment/argocd-repo-server",
                "statefulset/argocd-application-controller",
            ):
                cluster.kubectl(
                    "rollout", "status", resource, "--timeout=300s", namespace="argocd"
                )
            app_name = "local-oci-runtime"
            values = cluster.values()["runtime"]
            for component in (
                values["backend"],
                values["frontend"],
                *values.get("workers", {}).values(),
            ):
                component.pop("image", None)
                component["image"] = {"pullPolicy": "IfNotPresent"}
            application = {
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "Application",
                "metadata": {"name": app_name},
                "spec": {
                    "project": "local-oci",
                    "source": {
                        "repoURL": internal,
                        "targetRevision": "dev",
                        "path": ".",
                        "helm": {"releaseName": "oci-test", "valuesObject": values},
                    },
                    "destination": {
                        "server": "https://kubernetes.default.svc",
                        "namespace": cluster.namespace,
                    },
                    "syncPolicy": {
                        "automated": {"enabled": True, "prune": True, "selfHeal": True}
                    },
                },
            }

            def wait_digest(digest, old_job=None):
                def complete():
                    app = cluster.get("applications", app_name, namespace="argocd")
                    status = app.get("status", {})
                    sync = status.get("sync", {})
                    operation = status.get("operationState", {})
                    if operation.get("phase") in ("Failed", "Error"):
                        raise AssertionError(json.dumps(status, indent=2))
                    jobs = cluster.get("jobs")
                    return (
                        not app.get("operation")
                        and sync.get("revision") == digest
                        and sync.get("status") == "Synced"
                        and status.get("health", {}).get("status") == "Healthy"
                        and operation.get("phase") == "Succeeded"
                        and len(jobs) == 1
                        and jobs[0]["status"].get("succeeded") == 1
                        and jobs[0]["metadata"]["uid"] != old_job
                    )

                eventually(
                    complete,
                    timeout=900,
                    description="OCI digest, migration hook and healthy rollout",
                )
                return cluster.get("jobs")[0]["metadata"]["uid"]

            with tempfile.TemporaryDirectory(prefix="dnk-oci-packages-") as directory:
                previous_job = None
                for number in (1, 2):
                    images = {
                        target: {
                            "repository": "dnk-test/" + target,
                            "tag": "helm-test",
                            "digest": run(
                                "docker",
                                "image",
                                "inspect",
                                "--format",
                                "{{.Id}}",
                                "dnk-test/" + target + ":helm-test",
                            ).stdout.strip(),
                        }
                        for target in ("runtime", "frontend-runtime")
                    }
                    record = {
                        "schema": 1,
                        "channel": "dev",
                        "branch": "develop",
                        "source_sha": "local-test",
                        "build_sha": "local-test",
                        "app_version": "0.1.0",
                        "chart_version": f"0.3.3-dev.{number}.1",
                        "chart_repository": repository,
                        "deployment_revision": f"oci-local-{number}",
                        "images": images,
                    }
                    archive, config = package_chart(ROOT, Path(directory), record)
                    digest = registry.push_chart(repository, archive, config, record)
                    manifest = registry.manifest(repository + "@" + digest)
                    assert manifest["config"]["mediaType"] == HELM_CONFIG
                    assert len(manifest["layers"]) == 1
                    assert manifest["layers"][0]["mediaType"] == HELM_LAYER
                    pulled = Path(directory) / f"pulled-{number}"
                    run(
                        "oras",
                        "pull",
                        "--plain-http",
                        repository + "@" + digest,
                        "--output",
                        pulled,
                    )
                    assert (pulled / archive.name).read_bytes() == archive.read_bytes()
                    registry.alias(repository, digest, "dev")
                    if number == 1:
                        cluster.apply(
                            "oci-application", [application], namespace="argocd"
                        )
                    else:
                        cluster.kubectl(
                            "annotate",
                            "application",
                            app_name,
                            "argocd.argoproj.io/refresh=hard",
                            "--overwrite",
                            namespace="argocd",
                        )
                    previous_job = wait_digest(digest, previous_job)
                # Same immutable package, explicit prod-style retry with a fresh token.
                cluster.kubectl(
                    "patch",
                    "application",
                    app_name,
                    "--type=merge",
                    "-p",
                    json.dumps(
                        {
                            "spec": {
                                "syncPolicy": {"automated": None},
                                "source": {
                                    "targetRevision": digest,
                                    "helm": {
                                        "parameters": [
                                            {
                                                "name": "global.deployment.revision",
                                                "value": "oci-local-retry-3",
                                                "forceString": True,
                                            }
                                        ]
                                    },
                                },
                            },
                        }
                    ),
                    namespace="argocd",
                )
                cluster.kubectl(
                    "annotate",
                    "application",
                    app_name,
                    "argocd.argoproj.io/refresh=hard",
                    "--overwrite",
                    namespace="argocd",
                )

                def parameters_compared():
                    app = cluster.get("applications", app_name, namespace="argocd")
                    status = app.get("status", {})
                    compared = (
                        status.get("sync", {}).get("comparedTo", {}).get("source", {})
                    )
                    return (
                        not app.get("operation")
                        and status.get("operationState", {}).get("phase") != "Running"
                        and compared.get("targetRevision") == digest
                        and compared.get("helm", {}).get("parameters")
                        == app["spec"]["source"]["helm"]["parameters"]
                    )

                eventually(
                    parameters_compared,
                    timeout=90,
                    description="new parameters compared and auto-sync idle",
                )
                # Match ArgoCD's SetAppOperation: clear the previous operation
                # state as well as replacing the request, so no self-heal filter
                # survives and migration hooks run in a full Sync.
                cluster.kubectl(
                    "patch",
                    "application",
                    app_name,
                    "--type=json",
                    "-p",
                    json.dumps(
                        [
                            {
                                "op": "add",
                                "path": "/status/operationState",
                                "value": None,
                            },
                            {
                                "op": "add",
                                "path": "/operation",
                                "value": {
                                    "initiatedBy": {"username": "local-test"},
                                    "sync": {"revision": digest, "prune": True},
                                },
                            },
                        ]
                    ),
                    namespace="argocd",
                )
                wait_digest(digest, previous_job)
            print(
                "PASS: local OCI media types, pull, dev alias update, migration/rollout and explicit digest retry",
                flush=True,
            )
        finally:
            run("docker", "rm", "-f", name, check=False)


if __name__ == "__main__":
    integration()
