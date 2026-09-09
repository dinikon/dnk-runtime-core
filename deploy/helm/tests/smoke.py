#!/usr/bin/env python3
"""Build and test Core in an owned, disposable kind cluster.

Requires Docker, kind, kubectl, Helm, openssl, curl, Python and PyYAML. Uses a
private temporary kubeconfig; never reads or changes the user's active cluster.
HTTPS is terminated by a test Nginx pod. Ingress resources are contract-tested
separately by test_render.py; this does not install an Ingress controller.
"""

from __future__ import annotations

import argparse
import base64
import json
from html.parser import HTMLParser
from http.cookies import SimpleCookie
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import uuid

import yaml

from test_render import CORE, HELM, ROOT, UMBRELLA, core_values


def run(arguments, *, capture=False, check=True, **kwargs):
    return subprocess.run(
        arguments, check=check, text=True, capture_output=capture, **kwargs
    )


def validate_http_response(path, body, headers):
    if path.startswith("/api/"):
        json.loads(body)
    if path == "/api/session/":
        cookies = SimpleCookie()
        for line in headers.splitlines():
            if line.lower().startswith("set-cookie:"):
                cookies.load(line.split(":", 1)[1].strip())
        csrf = cookies["dnk_core_csrftoken"]
        assert (
            csrf["secure"] and csrf["httponly"]
        ), "CSRF cookie must be Secure and HttpOnly"
    if path == "/":

        class CanonicalParser(HTMLParser):
            canonical = None

            def handle_starttag(self, tag, attrs):
                attributes = dict(attrs)
                if tag == "link" and attributes.get("rel") == "canonical":
                    self.canonical = attributes.get("href")

        parser = CanonicalParser()
        parser.feed(body)
        assert parser.canonical == "https://core.example.test/", parser.canonical


def smoke(skip_build=False):
    for executable in ["docker", "kind", "kubectl", HELM, "openssl", "curl"]:
        if shutil.which(executable) is None:
            raise RuntimeError(f"Required executable is unavailable: {executable}")
    cluster = "dnk-helm-" + uuid.uuid4().hex[:8]
    namespace = "core-smoke"
    release = "smoke"
    forward = None
    created = False
    with tempfile.TemporaryDirectory(prefix="dnk-helm-smoke-") as directory:
        work = Path(directory)
        environment = os.environ | {"KUBECONFIG": str(work / "kubeconfig")}

        def kubectl(*args, capture=False, check=True):
            return run(
                [
                    "kubectl",
                    "--context",
                    "kind-" + cluster,
                    "--namespace",
                    namespace,
                    *args,
                ],
                capture=capture,
                check=check,
                env=environment,
            )

        def apply(name, resources):
            path = work / (name + ".yaml")
            path.write_text(yaml.safe_dump_all(resources))
            kubectl("apply", "-f", str(path))

        def resource_name(kind, component):
            result = kubectl(
                "get",
                kind,
                "-l",
                "app.kubernetes.io/component=" + component,
                "-o",
                "json",
                capture=True,
            )
            items = json.loads(result.stdout)["items"]
            if len(items) != 1:
                raise AssertionError(
                    f"Expected one {component} {kind}; found {len(items)}"
                )
            return items[0]["metadata"]["name"]

        def database(sql):
            return kubectl(
                "exec",
                "statefulset/" + resource_name("statefulset", "postgresql"),
                "--",
                "psql",
                "-U",
                "core",
                "-d",
                "dniko",
                "-v",
                "ON_ERROR_STOP=1",
                "-At",
                "-c",
                sql,
                capture=True,
            ).stdout.strip()

        def redis(*args):
            return kubectl(
                "exec",
                "statefulset/" + resource_name("statefulset", "redis"),
                "--",
                "redis-cli",
                "-n",
                "1",
                *args,
                capture=True,
            ).stdout.strip()

        def wait():
            for name in ["backend", "frontend", "gateway"]:
                kubectl(
                    "rollout",
                    "status",
                    "deployment/" + resource_name("deployment", name),
                    "--timeout=600s",
                )
            for name in ["postgresql", "redis"]:
                kubectl(
                    "rollout",
                    "status",
                    "statefulset/" + resource_name("statefulset", name),
                    "--timeout=300s",
                )

        try:
            if not skip_build:
                print("Building the three existing application images", flush=True)
                run(
                    [
                        "docker",
                        "build",
                        "-f",
                        "core/Dockerfile",
                        "-t",
                        "dnk-core:helm-test",
                        ".",
                    ],
                    cwd=ROOT,
                )
                for target, image in [
                    ("runtime", "dnk-core-web"),
                    ("gateway", "dnk-core-frontend"),
                ]:
                    run(
                        [
                            "docker",
                            "build",
                            "-f",
                            "apps/core/Dockerfile",
                            "--target",
                            target,
                            "-t",
                            image + ":helm-test",
                            ".",
                        ],
                        cwd=ROOT / "frontends",
                    )
            print("Creating disposable cluster " + cluster, flush=True)
            kind_config = work / "kind.yaml"
            kind_config.write_text(
                yaml.safe_dump(
                    {
                        "kind": "Cluster",
                        "apiVersion": "kind.x-k8s.io/v1alpha4",
                        "nodes": [{"role": "control-plane"}],
                    }
                )
            )
            # Set before create so even a partially created cluster is cleaned up.
            created = True
            run(
                [
                    "kind",
                    "create",
                    "cluster",
                    "--name",
                    cluster,
                    "--config",
                    str(kind_config),
                    "--kubeconfig",
                    str(work / "kubeconfig"),
                    "--wait",
                    "180s",
                ],
                env=environment,
            )
            run(
                [
                    "kind",
                    "load",
                    "docker-image",
                    "--name",
                    cluster,
                    "dnk-core:helm-test",
                    "dnk-core-web:helm-test",
                    "dnk-core-frontend:helm-test",
                ],
                env=environment,
            )
            kubectl("create", "namespace", namespace)
            values = core_values()
            for component in ["backend", "frontend", "gateway"]:
                values[component]["image"].update(
                    {"tag": "helm-test", "pullPolicy": "Never"}
                )
            values["backend"]["replicas"] = 2
            values["application"]["email"][
                "backend"
            ] = "django.core.mail.backends.locmem.EmailBackend"
            values["application"]["server"]["trustedProxyCount"] = 2
            values["postgresql"]["persistence"] = {"size": "256Mi"}
            values["redis"]["persistence"] = {"size": "256Mi"}
            values_path = work / "values.yaml"

            def install(chart=UMBRELLA):
                values_path.write_text(
                    yaml.safe_dump({"core": values} if chart == UMBRELLA else values)
                )
                run(
                    [
                        HELM,
                        "upgrade",
                        "--install",
                        release,
                        str(chart),
                        "--namespace",
                        namespace,
                        "--kube-context",
                        "kind-" + cluster,
                        "-f",
                        str(values_path),
                        "--wait",
                        "--timeout",
                        "12m",
                    ],
                    env=environment,
                )
                wait()

            print(
                "Installing with two backend replicas and serialized migrations",
                flush=True,
            )
            install()
            assert int(database("SELECT count(*) FROM core.django_migrations")) > 0
            database(
                "CREATE TABLE public.helm_probe (value text); INSERT INTO public.helm_probe VALUES ('public-ok'); CREATE SCHEMA tenant_helm_probe; CREATE TABLE tenant_helm_probe.sentinel (value text); INSERT INTO tenant_helm_probe.sentinel VALUES ('tenant-ok'); CREATE TABLE core.helm_probe (value text); INSERT INTO core.helm_probe VALUES ('core-ok');"
            )
            assert redis("SET", "helm:probe", "redis-ok") == "OK"

            print("Checking HTTPS routes through a dedicated TLS proxy", flush=True)
            key = work / "tls.key"
            certificate = work / "tls.crt"
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
                    "subjectAltName=DNS:core.example.test",
                    "-keyout",
                    str(key),
                    "-out",
                    str(certificate),
                ],
                capture=True,
            )
            gateway = resource_name("service", "gateway")
            gateway_ip = json.loads(
                kubectl("get", "service", gateway, "-o", "json", capture=True).stdout
            )["spec"]["clusterIP"]
            nginx = f"""server {{
  listen 8443 ssl;
  ssl_certificate /tls/tls.crt;
  ssl_certificate_key /tls/tls.key;
  location / {{
    proxy_pass http://{gateway_ip}:80;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header X-Forwarded-For $remote_addr;
  }}
}}
"""
            apply(
                "tls-proxy",
                [
                    {
                        "apiVersion": "v1",
                        "kind": "Secret",
                        "metadata": {"name": "smoke-tls"},
                        "type": "kubernetes.io/tls",
                        "data": {
                            "tls.crt": base64.b64encode(
                                certificate.read_bytes()
                            ).decode(),
                            "tls.key": base64.b64encode(key.read_bytes()).decode(),
                        },
                    },
                    {
                        "apiVersion": "v1",
                        "kind": "ConfigMap",
                        "metadata": {"name": "smoke-tls-proxy"},
                        "data": {"default.conf": nginx},
                    },
                    {
                        "apiVersion": "v1",
                        "kind": "Pod",
                        "metadata": {"name": "smoke-tls-proxy"},
                        "spec": {
                            "containers": [
                                {
                                    "name": "nginx",
                                    "image": "dnk-core-frontend:helm-test",
                                    "imagePullPolicy": "Never",
                                    "ports": [{"containerPort": 8443}],
                                    "volumeMounts": [
                                        {
                                            "name": "configuration",
                                            "mountPath": "/etc/nginx/conf.d",
                                        },
                                        {
                                            "name": "tls",
                                            "mountPath": "/tls",
                                            "readOnly": True,
                                        },
                                    ],
                                }
                            ],
                            "volumes": [
                                {
                                    "name": "configuration",
                                    "configMap": {"name": "smoke-tls-proxy"},
                                },
                                {"name": "tls", "secret": {"secretName": "smoke-tls"}},
                            ],
                        },
                    },
                ],
            )
            kubectl(
                "wait", "pod/smoke-tls-proxy", "--for=condition=Ready", "--timeout=120s"
            )
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            log = (work / "port-forward.log").open("w")
            forward = subprocess.Popen(
                [
                    "kubectl",
                    "--context",
                    "kind-" + cluster,
                    "--namespace",
                    namespace,
                    "port-forward",
                    "pod/smoke-tls-proxy",
                    f"{port}:8443",
                    "--address",
                    "127.0.0.1",
                ],
                env=environment,
                stdout=log,
                stderr=log,
            )
            deadline = time.monotonic() + 30
            while True:
                if forward.poll() is not None:
                    raise RuntimeError((work / "port-forward.log").read_text())
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=1):
                        break
                except OSError:
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(0.2)

            def check_http():
                for path, statuses in [
                    ("/", {200}),
                    ("/api/capabilities/", {200}),
                    ("/api/session/", {200}),
                    ("/accounts/login/", {200}),
                    ("/admin/", {302}),
                    ("/static/admin/css/base.css", {200}),
                ]:
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
                            f"core.example.test:{port}:127.0.0.1",
                            "--max-time",
                            "30",
                            "--output",
                            str(work / "body"),
                            "--dump-header",
                            str(work / "headers"),
                            "--write-out",
                            "%{http_code}",
                            f"https://core.example.test:{port}{path}",
                        ],
                        capture=True,
                    )
                    if int(result.stdout) not in statuses:
                        raise AssertionError(
                            f"{path}: unexpected HTTP {result.stdout}: {(work / 'headers').read_text()} {(work / 'body').read_text()[:1000]}"
                        )
                    validate_http_response(
                        path,
                        (work / "body").read_text(),
                        (work / "headers").read_text(),
                    )
                print("All six HTTPS routes passed", flush=True)

            def check_data():
                assert database("SELECT value FROM public.helm_probe") == "public-ok"
                assert (
                    database("SELECT value FROM tenant_helm_probe.sentinel")
                    == "tenant-ok"
                )
                assert database("SELECT value FROM core.helm_probe") == "core-ok"
                assert redis("GET", "helm:probe") == "redis-ok"

            check_http()
            print("Upgrading backend configuration and replicas", flush=True)
            values["backend"]["replicas"] = 3
            values["application"]["server"]["timeZone"] = "Europe/Kyiv"
            install()
            check_data()
            check_http()
            print("Restarting data pods and verifying persistence", flush=True)
            for component in ["postgresql", "redis"]:
                kubectl(
                    "delete",
                    "pod",
                    "-l",
                    "app.kubernetes.io/component=" + component,
                    "--wait=true",
                )
            wait()
            check_data()
            print(
                "Uninstalling, preserving PVCs, and reinstalling standalone Core",
                flush=True,
            )
            claims_before = json.loads(
                kubectl("get", "pvc", "-o", "json", capture=True).stdout
            )["items"]
            assert len(claims_before) == 2
            claim_uids = {claim["metadata"]["uid"] for claim in claims_before}
            run(
                [
                    HELM,
                    "uninstall",
                    release,
                    "--namespace",
                    namespace,
                    "--kube-context",
                    "kind-" + cluster,
                    "--wait",
                ],
                env=environment,
            )
            claims_after = json.loads(
                kubectl("get", "pvc", "-o", "json", capture=True).stdout
            )["items"]
            assert {claim["metadata"]["uid"] for claim in claims_after} == claim_uids
            install(CORE)
            check_data()
            # Service recreation changes ClusterIP. Refresh the fixture through the API
            # so a cached DNS answer cannot keep the test proxy on the deleted Service.
            new_gateway_ip = json.loads(
                kubectl("get", "service", gateway, "-o", "json", capture=True).stdout
            )["spec"]["clusterIP"]
            nginx = nginx.replace(
                f"http://{gateway_ip}:80", f"http://{new_gateway_ip}:80"
            )
            apply(
                "tls-proxy-refresh",
                [
                    {
                        "apiVersion": "v1",
                        "kind": "ConfigMap",
                        "metadata": {"name": "smoke-tls-proxy"},
                        "data": {"default.conf": nginx},
                    }
                ],
            )
            # Wait for the projected ConfigMap before reloading only the test proxy.
            # The application chart itself is not patched by this test.
            kubectl(
                "exec",
                "smoke-tls-proxy",
                "--",
                "sh",
                "-ec",
                'attempts=0; until test "$(cat /etc/nginx/conf.d/default.conf)" = "$1"; do attempts=$((attempts + 1)); test "$attempts" -lt 120; sleep 1; done; nginx -s reload',
                "sh",
                nginx.rstrip(),
            )
            time.sleep(1)
            check_http()
            print(
                "PASS: installation, migration concurrency, upgrade, HTTPS routes, restart and uninstall/reinstall persistence",
                flush=True,
            )
        except BaseException:
            if created and (work / "kubeconfig").exists():
                kubectl("get", "pods,pvc,events", capture=False, check=False)
                for component in [
                    "backend",
                    "frontend",
                    "gateway",
                    "postgresql",
                    "redis",
                ]:
                    kubectl(
                        "logs",
                        "-l",
                        "app.kubernetes.io/component=" + component,
                        "--all-containers",
                        "--tail=100",
                        "--prefix=true",
                        check=False,
                    )
            raise
        finally:
            if forward is not None:
                forward.terminate()
                forward.wait(timeout=10)
            if created:
                run(
                    ["kind", "delete", "cluster", "--name", cluster],
                    env=environment,
                    check=False,
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-build", action="store_true", help="Reuse local :helm-test images"
    )
    smoke(skip_build=parser.parse_args().skip_build)
