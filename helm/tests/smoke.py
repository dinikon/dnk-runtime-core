#!/usr/bin/env python3
"""Verify the standalone Runtime chart using only this repository's images."""

import argparse
import time
import yaml
from cluster import Cluster, run, eventually
from test_render import HELM, RUNTIME
from runtime_https_fixture import check_runtime_auth
from system_ingress import setup_system_ingress, certificate_endpoint


def wait_for_gate(cluster, deployment, expected):
    pods = cluster.get(
        "pods",
        selector="app.kubernetes.io/component="
        + deployment["metadata"]["labels"]["app.kubernetes.io/component"]
        + ",app.kubernetes.io/name="
        + deployment["metadata"]["labels"]["app.kubernetes.io/name"],
    )
    running = [
        p
        for p in pods
        if any(
            s.get("state", {}).get("running")
            for s in p.get("status", {}).get("initContainerStatuses", [])
            if s["name"] == "wait-migrations"
        )
    ]
    return len(running) >= expected


def check_gate_api_failures(cluster):
    """Exercise the real Kubernetes API with absent and stale retained Jobs."""
    job = next(
        j for j in cluster.get("jobs") if "runtime-core" in j["metadata"]["name"]
    )
    job_name = job["metadata"]["name"]
    original_token = job["metadata"]["annotations"]["dnk.io/deployment-token"]
    cluster.kubectl(
        "annotate",
        "job/" + job_name,
        "dnk.io/deployment-token=stale-test",
        "--overwrite",
    )
    deployments = cluster.get("deployments")
    old_replicas = {d["metadata"]["name"]: d["spec"]["replicas"] for d in deployments}
    for deployment in deployments:
        cluster.kubectl(
            "scale",
            "deployment/" + deployment["metadata"]["name"],
            "--replicas=" + str(deployment["spec"]["replicas"] + 1),
        )
    eventually(
        lambda: all(wait_for_gate(cluster, d, 1) for d in deployments),
        timeout=120,
        description="all packages blocked by stale Runtime Job",
    )
    cluster.kubectl("delete", "job/" + job_name, "--wait=true")
    time.sleep(5)
    assert all(
        wait_for_gate(cluster, d, 1) for d in deployments
    ), "missing Job bypassed barrier"
    metadata = {
        "name": job_name,
        "annotations": job["metadata"]["annotations"],
        "labels": job["metadata"].get("labels", {}),
    }
    metadata["annotations"]["dnk.io/deployment-token"] = original_token
    spec = job["spec"]
    spec.pop("selector", None)
    for label in [
        "controller-uid",
        "batch.kubernetes.io/controller-uid",
        "job-name",
        "batch.kubernetes.io/job-name",
    ]:
        spec["template"]["metadata"].get("labels", {}).pop(label, None)
    cluster.apply(
        "recreate-job",
        [{"apiVersion": "batch/v1", "kind": "Job", "metadata": metadata, "spec": spec}],
    )
    cluster.kubectl(
        "wait", "job/" + job_name, "--for=condition=Complete", "--timeout=600s"
    )
    cluster.rollout()
    for name, replicas in old_replicas.items():
        cluster.kubectl("scale", "deployment/" + name, "--replicas=" + str(replicas))
    print(
        "PASS: stale or absent Runtime Job blocks every application; retained success permits scaling",
        flush=True,
    )


def check_https(cluster, endpoint):
    port = cluster.port_forward(endpoint["resource"], 443, namespace="ingress-nginx")
    check_runtime_auth(cluster, (port, endpoint["certificate"]))
    for path in ["/", "/login"]:
        response = run(
            [
                "curl",
                "--fail",
                "--silent",
                "--show-error",
                "--noproxy",
                "*",
                "--cacert",
                str(endpoint["certificate"]),
                "--resolve",
                f"runtime.example.test:{port}:127.0.0.1",
                f"https://runtime.example.test:{port}{path}",
            ],
            capture=True,
        )
        assert response.stdout


def smoke(reuse_test_images=False):
    with Cluster(reuse_test_images=reuse_test_images) as cluster:
        values = cluster.values()["runtime"]
        authority = setup_system_ingress(cluster)
        values["ingress"] = {"enabled": True, "className": "nginx"}
        values_file = cluster.work / "values.yaml"

        def install():
            values_file.write_text(yaml.safe_dump(values))
            run(
                [
                    HELM,
                    "upgrade",
                    "--install",
                    "smoke",
                    str(RUNTIME),
                    "--namespace",
                    cluster.namespace,
                    "--kube-context",
                    "kind-" + cluster.name,
                    "-f",
                    str(values_file),
                    "--wait",
                    "--wait-for-jobs",
                    "--timeout",
                    "12m",
                ],
                env=cluster.environment,
            )
            cluster.rollout()

        install()
        jobs = cluster.get("jobs")
        assert len(jobs) == 1 and jobs[0]["status"].get("succeeded") == 1
        assert (
            cluster.database("runtime", "SELECT to_regclass('public.tenants')")
            == "tenants"
        )
        cluster.database(
            "runtime",
            "CREATE TABLE public.helm_probe(value text); INSERT INTO public.helm_probe VALUES ('public-ok'); CREATE SCHEMA tenant_helm_probe; CREATE TABLE tenant_helm_probe.sentinel(value text); INSERT INTO tenant_helm_probe.sentinel VALUES ('tenant-ok');",
        )
        assert cluster.redis("runtime", "SET", "helm:persistence", "runtime") == "OK"
        cluster.rabbitmq("add_vhost", "helm-persistence")
        endpoint = certificate_endpoint(cluster, authority)
        check_https(cluster, endpoint)
        check_gate_api_failures(cluster)
        values["global"] = {"deployment": {"revision": "runtime-upgrade-2"}}
        values["backend"]["replicas"] = 3
        install()
        jobs = cluster.get("jobs")
        assert len(jobs) == 1 and jobs[0]["metadata"]["name"].endswith("-migrate-r2")
        claims = {claim["metadata"]["uid"] for claim in cluster.get("pvc")}
        assert len(claims) == 3
        for statefulset in cluster.get("statefulsets"):
            cluster.kubectl(
                "delete",
                "pod",
                "-l",
                "app.kubernetes.io/instance=smoke,app.kubernetes.io/name="
                + statefulset["metadata"]["labels"]["app.kubernetes.io/name"],
                "--wait=true",
            )
        cluster.rollout()

        def data_intact():
            assert (
                cluster.database("runtime", "SELECT value FROM public.helm_probe")
                == "public-ok"
            )
            assert (
                cluster.database(
                    "runtime", "SELECT value FROM tenant_helm_probe.sentinel"
                )
                == "tenant-ok"
            )
            assert cluster.redis("runtime", "GET", "helm:persistence") == "runtime"
            assert "helm-persistence" in cluster.rabbitmq("list_vhosts", "--silent")

        data_intact()
        run(
            [
                HELM,
                "uninstall",
                "smoke",
                "--namespace",
                cluster.namespace,
                "--kube-context",
                "kind-" + cluster.name,
                "--wait",
            ],
            env=cluster.environment,
        )
        assert {claim["metadata"]["uid"] for claim in cluster.get("pvc")} == claims
        install()
        data_intact()
        check_https(cluster, endpoint)
        print(
            "PASS: Runtime standalone install/upgrade, migration gate, HTTPS and retained data",
            flush=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reuse-test-images",
        action="store_true",
        help="Use already built dnk-test Runtime image tags",
    )
    args = parser.parse_args()
    smoke(reuse_test_images=args.reuse_test_images)
