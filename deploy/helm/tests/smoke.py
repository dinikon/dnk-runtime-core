#!/usr/bin/env python3
"""Install both packages in an owned kind cluster; verify Jobs, HTTPS and PVCs.

Default builds local test tags. --published-images reuses the four published
images without modifying their tags. No active kubeconfig or cluster is used.
"""

from __future__ import annotations

import argparse
import base64
import json
from http.cookies import SimpleCookie
import time

import yaml

from cluster import Cluster, run, eventually
from test_render import CORE, RUNTIME, UMBRELLA, HELM


def tls_proxy(cluster):
    certificate = cluster.work / "tls.crt"
    key = cluster.work / "tls.key"
    run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-subj",
            "/CN=core.example.test",
            "-addext",
            "subjectAltName=DNS:core.example.test,DNS:runtime.example.test",
            "-keyout",
            str(key),
            "-out",
            str(certificate),
        ],
        capture=True,
    )
    configuration = ""
    for app, host in [
        ("controlPlane", "core.example.test"),
        ("runtime", "runtime.example.test"),
    ]:
        service = cluster.name_for("service", app, "gateway")
        configuration += f"""server {{
 listen 8443 ssl;
 server_name {host};
 ssl_certificate /tls/tls.crt;
 ssl_certificate_key /tls/tls.key;
 resolver kube-dns.kube-system.svc.cluster.local valid=1s;
 set $upstream {service}.{cluster.namespace}.svc.cluster.local;
 location / {{
  proxy_pass http://$upstream:80;
  proxy_set_header Host $host;
  proxy_set_header X-Forwarded-Proto https;
  proxy_set_header X-Forwarded-For $remote_addr;
 }}
}}
"""
    cluster.apply(
        "tls-proxy",
        [
            {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": "test-tls"},
                "type": "kubernetes.io/tls",
                "data": {
                    "tls.crt": base64.b64encode(certificate.read_bytes()).decode(),
                    "tls.key": base64.b64encode(key.read_bytes()).decode(),
                },
            },
            {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {"name": "test-tls-proxy"},
                "data": {"default.conf": configuration},
            },
            {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {"name": "test-tls-proxy"},
                "spec": {
                    "containers": [
                        {
                            "name": "nginx",
                            "image": "nginx:1.27-alpine",
                            "imagePullPolicy": "Never",
                            "ports": [{"containerPort": 8443}],
                            "volumeMounts": [
                                {"name": "config", "mountPath": "/etc/nginx/conf.d"},
                                {"name": "tls", "mountPath": "/tls", "readOnly": True},
                            ],
                        }
                    ],
                    "volumes": [
                        {"name": "config", "configMap": {"name": "test-tls-proxy"}},
                        {"name": "tls", "secret": {"secretName": "test-tls"}},
                    ],
                },
            },
        ],
    )
    cluster.kubectl(
        "wait", "pod/test-tls-proxy", "--for=condition=Ready", "--timeout=120s"
    )
    return cluster.port_forward("pod/test-tls-proxy", 8443), certificate


def check_https(cluster, proxy):
    from runtime_https_fixture import check_runtime_auth

    # Reopen the fixture tunnel per check; a test-node runtime restart can close
    # a long-lived kubectl stream without affecting the healthy TLS proxy pod.
    _, certificate = proxy
    port = cluster.port_forward("pod/test-tls-proxy", 8443)
    check_runtime_auth(cluster, (port, certificate))
    for host, paths in [
        (
            "core.example.test",
            [
                ("/", {200}),
                ("/api/capabilities/", {200}),
                ("/api/session/", {200}),
                ("/accounts/login/", {200}),
                ("/admin/", {302}),
                ("/static/admin/css/base.css", {200}),
            ],
        ),
        (
            "runtime.example.test",
            [
                ("/", {200}),
                ("/login", {200}),
                ("/api/console/auth/me", {401}),
            ],
        ),
    ]:
        for path, statuses in paths:
            result = run(
                [
                    "curl",
                    "--silent",
                    "--show-error",
                    "--noproxy",
                    "*",
                    "--cacert",
                    str(certificate),
                    "--resolve",
                    f"{host}:{port}:127.0.0.1",
                    "--max-time",
                    "30",
                    "--output",
                    str(cluster.work / "body"),
                    "--dump-header",
                    str(cluster.work / "headers"),
                    "--write-out",
                    "%{http_code}",
                    f"https://{host}:{port}{path}",
                ],
                capture=True,
            )
            body = (cluster.work / "body").read_text()
            headers = (cluster.work / "headers").read_text()
            assert int(result.stdout) in statuses, (
                host,
                path,
                result.stdout,
                headers,
                body[:800],
            )
            if path.startswith("/api/"):
                assert isinstance(json.loads(body), (dict, list))
            elif int(result.stdout) == 200 and not path.startswith("/static/"):
                assert "<" in body
            if path == "/api/session/":
                cookies = SimpleCookie()
                for line in headers.splitlines():
                    if line.lower().startswith("set-cookie:"):
                        cookies.load(line.split(":", 1)[1].strip())
                assert (
                    cookies["dnk_core_csrftoken"]["secure"]
                    and cookies["dnk_core_csrftoken"]["httponly"]
                )
    print(
        "PASS: both frontends and API/authentication routes through HTTPS", flush=True
    )


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


def smoke(published=False):
    with Cluster(published=published) as cluster:
        values = cluster.values()
        values_file = cluster.work / "values.yaml"

        def install(chart=UMBRELLA, release="smoke", selected=None):
            values_file.write_text(
                yaml.safe_dump(values if selected is None else values[selected])
            )
            run(
                [
                    HELM,
                    "upgrade",
                    "--install",
                    release,
                    str(chart),
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

        print(
            "Installing complete platform with two backend replicas per package",
            flush=True,
        )
        install()
        jobs = cluster.get("jobs")
        assert len(jobs) == 2 and all(j["status"].get("succeeded") == 1 for j in jobs)
        assert all(j["metadata"]["name"].endswith("-migrate-r1") for j in jobs)
        assert (
            int(
                cluster.database(
                    "controlPlane", "SELECT count(*) FROM core.django_migrations"
                )
            )
            > 0
        )
        assert (
            cluster.database("runtime", "SELECT to_regclass('public.tenants')")
            == "tenants"
        )
        for app in ["controlPlane", "runtime"]:
            cluster.database(
                app,
                "CREATE TABLE public.helm_probe(value text); INSERT INTO public.helm_probe VALUES ('public-ok'); CREATE SCHEMA tenant_helm_probe; CREATE TABLE tenant_helm_probe.sentinel(value text); INSERT INTO tenant_helm_probe.sentinel VALUES ('tenant-ok');",
            )
        for app in ["controlPlane", "runtime"]:
            assert cluster.redis(app, "SET", "helm:persistence", app) == "OK"
        cluster.rabbitmq("add_vhost", "helm-persistence")
        proxy = tls_proxy(cluster)
        check_https(cluster, proxy)
        check_gate_api_failures(cluster)
        print(
            "Upgrading full platform and verifying both migration Jobs run again",
            flush=True,
        )
        values["global"] = {"deployment": {"revision": "smoke-git-revision-2"}}
        for app in ["controlPlane", "runtime"]:
            values[app]["backend"]["replicas"] = 3
        install()
        jobs = cluster.get("jobs")
        assert len(jobs) == 2 and all(
            j["metadata"]["name"].endswith("-migrate-r2")
            and j["status"].get("succeeded") == 1
            for j in jobs
        )
        check_https(cluster, proxy)
        claims = {p["metadata"]["uid"] for p in cluster.get("pvc")}
        assert len(claims) == 5
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
            assert "helm-persistence" in cluster.rabbitmq("list_vhosts", "--silent")
            for app in ["controlPlane", "runtime"]:
                assert (
                    cluster.database(app, "SELECT value FROM public.helm_probe")
                    == "public-ok"
                )
                assert (
                    cluster.database(
                        app, "SELECT value FROM tenant_helm_probe.sentinel"
                    )
                    == "tenant-ok"
                )

                assert cluster.redis(app, "GET", "helm:persistence") == app

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
        assert {p["metadata"]["uid"] for p in cluster.get("pvc")} == claims
        print("Reinstalling both independent packages using retained PVCs", flush=True)
        # Same release name preserves the default resource names and retained PVCs.
        install(CORE, selected="controlPlane")
        # Separate Helm release must explicitly retain the original full names.
        for component in ["postgresql", "redis", "rabbitmq"]:
            values["runtime"][component]["fullnameOverride"] = (
                "smoke-runtime-" + component
            )
        values["runtime"]["fullnameOverride"] = "smoke-dnk-runtime-core"
        install(RUNTIME, release="runtime", selected="runtime")
        data_intact()
        check_https(cluster, proxy)
        print(
            "PASS: complete and standalone installs, revision Jobs, replicas, HTTPS, data restart/reinstall retention",
            flush=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--published-images",
        "--skip-build",
        action="store_true",
        dest="published",
        help="Use existing published image tags instead of building local test images",
    )
    smoke(published=parser.parse_args().published)
