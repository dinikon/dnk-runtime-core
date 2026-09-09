#!/usr/bin/env python3
"""Real ArgoCD Sync/wave/selfHeal contracts in an owned, disposable kind cluster.

A temporary copy of the working chart is served by a local Git HTTP Service.
Nothing is pushed to GitHub and no user kubeconfig or existing cluster is used.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import time

import yaml

from cluster import Cluster, run, eventually, KIND
from test_render import UMBRELLA
from smoke import check_https, tls_proxy, wait_for_gate

ARGOCD_VERSION = os.environ.get("ARGOCD_VERSION", "v3.1.8")
CORE_LOCK_ID = int.from_bytes(b"dnk:core", "big")


def install_argocd(cluster):
    cluster.kubectl("create", "namespace", "argocd")
    manifest = cluster.work / "argocd.yaml"
    run(
        [
            "curl",
            "--fail",
            "--location",
            "--silent",
            "--show-error",
            f"https://raw.githubusercontent.com/argoproj/argo-cd/{ARGOCD_VERSION}/manifests/core-install.yaml",
            "-o",
            str(manifest),
        ]
    )
    cluster.kubectl("apply", "--server-side", "-f", str(manifest), namespace="argocd")
    # Core mode omits argocd-server, which normally initializes this setting.
    cluster.apply(
        "argocd-core-settings",
        [
            {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": "argocd-secret", "namespace": "argocd"},
                "stringData": {"server.secretkey": os.urandom(32).hex()},
            }
        ],
        namespace="argocd",
    )
    for kind, name in [
        ("statefulset", "argocd-application-controller"),
        ("deployment", "argocd-repo-server"),
        ("deployment", "argocd-redis"),
    ]:
        cluster.kubectl(
            "rollout", "status", kind + "/" + name, "--timeout=600s", namespace="argocd"
        )


def serve_git(cluster):
    working = cluster.work / "repository"
    working.mkdir()
    shutil.copytree(UMBRELLA, working / "deploy/helm/dnk-platform")
    run(["git", "init", "-b", "main", str(working)], capture=True)
    run(
        [
            "git",
            "-C",
            str(working),
            "config",
            "user.name",
            "DNK disposable integration test",
        ]
    )
    run(["git", "-C", str(working), "config", "user.email", "test@example.invalid"])
    bare = cluster.git_directory / "repo.git"
    run(["git", "init", "--bare", str(bare)], capture=True)
    run(["git", "-C", str(working), "remote", "add", "origin", str(bare)])

    def commit(message):
        (working / "test-revision.txt").write_text(message)
        run(["git", "-C", str(working), "add", "."])
        run(["git", "-C", str(working), "commit", "-m", message], capture=True)
        run(["git", "-C", str(working), "push", "origin", "main"], capture=True)
        run(["git", "--git-dir", str(bare), "symbolic-ref", "HEAD", "refs/heads/main"])
        run(["git", "--git-dir", str(bare), "update-server-info"])
        return run(
            ["git", "-C", str(working), "rev-parse", "HEAD"], capture=True
        ).stdout.strip()

    revision = commit("Initial working-chart snapshot")
    cluster.apply(
        "git-server",
        [
            {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {"name": "test-git", "labels": {"app": "test-git"}},
                "spec": {
                    "containers": [
                        {
                            "name": "nginx",
                            "image": "nginx:1.27-alpine",
                            "imagePullPolicy": "Never",
                            "volumeMounts": [
                                {
                                    "name": "repository",
                                    "mountPath": "/usr/share/nginx/html",
                                    "readOnly": True,
                                }
                            ],
                        }
                    ],
                    "volumes": [
                        {
                            "name": "repository",
                            "hostPath": {"path": "/dnk-test-git", "type": "Directory"},
                        }
                    ],
                },
            },
            {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {"name": "test-git"},
                "spec": {
                    "selector": {"app": "test-git"},
                    "ports": [{"port": 80, "targetPort": 80}],
                },
            },
        ],
        namespace="argocd",
    )
    cluster.kubectl(
        "wait",
        "pod/test-git",
        "--for=condition=Ready",
        "--timeout=120s",
        namespace="argocd",
    )
    return commit, revision


def argocd_smoke(published=False, reuse_test_images=False):
    with Cluster(
        published=published,
        namespace="argo-platform",
        reuse_test_images=reuse_test_images,
    ) as cluster:
        install_argocd(cluster)
        commit, revision = serve_git(cluster)
        values = cluster.values()
        application = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Application",
            "metadata": {"name": "dnk-test", "namespace": "argocd"},
            "spec": {
                "project": "default",
                "destination": {
                    "server": "https://kubernetes.default.svc",
                    "namespace": cluster.namespace,
                },
                "source": {
                    "repoURL": "http://test-git.argocd.svc.cluster.local/repo.git",
                    "path": "deploy/helm/dnk-platform",
                    "targetRevision": "main",
                    "helm": {
                        "releaseName": "smoke",
                        "values": yaml.safe_dump(values),
                        "parameters": [
                            {
                                "name": "global.deployment.revision",
                                "value": "$ARGOCD_APP_REVISION",
                                "forceString": True,
                            }
                        ],
                    },
                },
                "syncPolicy": {"syncOptions": ["CreateNamespace=true"]},
            },
        }
        cluster.apply(
            "test-project",
            [
                {
                    "apiVersion": "argoproj.io/v1alpha1",
                    "kind": "AppProject",
                    "metadata": {"name": "default", "namespace": "argocd"},
                    "spec": {
                        "sourceRepos": [
                            "http://test-git.argocd.svc.cluster.local/repo.git"
                        ],
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
                }
            ],
            namespace="argocd",
        )
        cluster.apply("application", [application], namespace="argocd")

        def app():
            return cluster.get("application", "dnk-test", namespace="argocd")

        def sync(revision, success=True):
            cluster.kubectl(
                "annotate",
                "application/dnk-test",
                "argocd.argoproj.io/refresh=hard",
                "--overwrite",
                namespace="argocd",
            )
            previous = (
                app().get("status", {}).get("operationState", {}).get("startedAt")
            )
            cluster.kubectl(
                "patch",
                "application/dnk-test",
                "--type=merge",
                "-p",
                json.dumps(
                    {
                        "operation": {
                            "initiatedBy": {"username": "disposable-test"},
                            "sync": {"revision": revision, "prune": True},
                        }
                    }
                ),
                namespace="argocd",
            )

            def finished():
                state = app().get("status", {}).get("operationState", {})
                if state.get("startedAt") == previous:
                    return False
                if state.get("phase") in {"Succeeded", "Failed", "Error"}:
                    return state
                return False

            return finished

        def wait_sync(predicate, success=True):
            state = eventually(
                predicate, timeout=900, description="ArgoCD sync completion"
            )
            assert (state["phase"] == "Succeeded") == success, json.dumps(
                state, indent=2
            )
            return state

        def job_uids():
            return {
                j["metadata"]["name"]: j["metadata"]["uid"] for j in cluster.get("jobs")
            }

        def pod_uids():
            return {
                p["metadata"]["uid"]
                for p in cluster.get("pods")
                if p["metadata"].get("labels", {}).get("app.kubernetes.io/component")
                in {"backend", "frontend", "gateway", "publisher"}
            }

        print(
            "ArgoCD initial full Sync: dependencies, migration Jobs, applications",
            flush=True,
        )
        wait_sync(sync(revision))
        cluster.rollout()
        jobs = cluster.get("jobs")
        assert len(jobs) == 2
        latest_completion = max(j["status"]["completionTime"] for j in jobs)
        assert all(
            d["metadata"]["creationTimestamp"] >= latest_completion
            for d in cluster.get("deployments")
        ), "wave 0 deployed before both migrations completed"
        proxy = tls_proxy(cluster)
        check_https(cluster, proxy)

        print(
            "ArgoCD repeated full Sync recreates Jobs while keeping healthy application pods",
            flush=True,
        )
        before_jobs, before_pods = job_uids(), pod_uids()
        time.sleep(1)
        wait_sync(sync(revision))
        assert all(before_jobs[name] != uid for name, uid in job_uids().items())
        assert (
            before_pods == pod_uids()
        ), "unchanged full Sync restarted application pods"

        print(
            "ArgoCD selfHeal restores drift without deleting successful migration Jobs",
            flush=True,
        )
        before_jobs = job_uids()
        cluster.kubectl(
            "patch",
            "application/dnk-test",
            "--type=merge",
            "-p",
            json.dumps(
                {
                    "spec": {
                        "syncPolicy": {"automated": {"prune": True, "selfHeal": True}}
                    }
                }
            ),
            namespace="argocd",
        )
        deployment = cluster.get("deployments")[0]
        name = deployment["metadata"]["name"]
        replicas = deployment["spec"]["replicas"]
        cluster.kubectl(
            "scale", "deployment/" + name, "--replicas=" + str(replicas + 1)
        )
        eventually(
            lambda: cluster.get("deployment", name)["spec"]["replicas"] == replicas,
            timeout=180,
            description="selfHeal replica drift",
        )
        assert before_jobs == job_uids(), "selfHeal reran migration hooks"
        cluster.kubectl(
            "patch",
            "application/dnk-test",
            "--type=merge",
            "-p",
            '{"spec":{"syncPolicy":{"automated":null}}}',
            namespace="argocd",
        )
        cluster.rollout()

        def hold_lock(seconds):
            database = next(
                s
                for s in cluster.get("statefulsets")
                if s["metadata"]["name"].endswith("control-plane-postgresql")
            )
            process = subprocess.Popen(
                [
                    "kubectl",
                    "--context",
                    "kind-" + cluster.name,
                    "--namespace",
                    cluster.namespace,
                    "exec",
                    "statefulset/" + database["metadata"]["name"],
                    "--",
                    "psql",
                    "-U",
                    "core",
                    "-d",
                    "dniko",
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-c",
                    f"SELECT pg_advisory_lock({CORE_LOCK_ID}); SELECT pg_sleep({seconds});",
                ],
                env=cluster.environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            eventually(
                lambda: cluster.database(
                    "controlPlane",
                    "SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND granted",
                )
                != "0",
                timeout=30,
                description="test database lock",
            )
            return process

        print(
            "ArgoCD delayed migration holds wave 0 and both packages' new pods",
            flush=True,
        )
        lock = hold_lock(45)
        before_jobs = job_uids()
        finished = sync(revision)
        eventually(
            lambda: job_uids() != before_jobs
            and any(j.get("status", {}).get("active") for j in cluster.get("jobs")),
            timeout=60,
            description="delayed migration Job",
        )
        deployments = cluster.get("deployments")
        for deployment in deployments:
            cluster.kubectl(
                "scale",
                "deployment/" + deployment["metadata"]["name"],
                "--replicas=" + str(deployment["spec"]["replicas"] + 1),
            )
        eventually(
            lambda: all(wait_for_gate(cluster, d, 1) for d in deployments),
            timeout=35,
            description="shared gate during delayed migration",
        )
        lock.wait(timeout=60)
        wait_sync(finished)
        cluster.rollout()

        print(
            "ArgoCD failed migration prevents applying the next application revision",
            flush=True,
        )
        values["controlPlane"]["migrations"] = {
            "waitTimeoutSeconds": 5,
            "activeDeadlineSeconds": 40,
            "backoffLimit": 0,
        }
        cluster.kubectl(
            "patch",
            "application/dnk-test",
            "--type=merge",
            "-p",
            json.dumps(
                {"spec": {"source": {"helm": {"values": yaml.safe_dump(values)}}}}
            ),
            namespace="argocd",
        )
        revision = commit("Fail a test migration while the advisory lock is held")
        lock = hold_lock(45)
        templates = {
            d["metadata"]["name"]: d["spec"]["template"]
            for d in cluster.get("deployments")
        }
        wait_sync(sync(revision), success=False)
        assert any(
            any(
                c.get("type") == "Failed" and c.get("status") == "True"
                for c in j.get("status", {}).get("conditions", [])
            )
            for j in cluster.get("jobs")
        )
        assert templates == {
            d["metadata"]["name"]: d["spec"]["template"]
            for d in cluster.get("deployments")
        }, "failed migration applied new app templates"
        lock.wait(timeout=60)
        values["controlPlane"]["migrations"] = {
            "waitTimeoutSeconds": 300,
            "activeDeadlineSeconds": 600,
            "backoffLimit": 1,
        }
        cluster.kubectl(
            "patch",
            "application/dnk-test",
            "--type=merge",
            "-p",
            json.dumps(
                {"spec": {"source": {"helm": {"values": yaml.safe_dump(values)}}}}
            ),
            namespace="argocd",
        )
        revision = commit("Recover the migration and deploy a new Git revision")
        previous_pods = pod_uids()
        wait_sync(sync(revision))
        cluster.rollout()
        assert not (
            previous_pods & pod_uids()
        ), "new Git revision did not roll every application pod"
        check_https(cluster, proxy)
        print(
            "PASS: real ArgoCD waves, full Sync, selfHeal, delayed/failed migrations, shared gate and Git revision rollout",
            flush=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--published-images", action="store_true")
    parser.add_argument("--reuse-test-images", action="store_true")
    args = parser.parse_args()
    argocd_smoke(
        published=args.published_images, reuse_test_images=args.reuse_test_images
    )
