"""Helpers restricted to a newly-created, disposable kind cluster."""

from __future__ import annotations

from contextlib import AbstractContextManager
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import uuid

import yaml

from test_render import HELM, ROOT, platform_values

KIND = os.environ.get("KIND", "kind")
PUBLIC_IMAGES = {
    "controlPlane": {"backend": "core", "frontend": "frontend-core"},
    "runtime": {"backend": "runtime", "frontend": "frontend-runtime"},
}
INFRA_IMAGES = [
    "nginx:1.27-alpine",
    "postgres:16-alpine",
    "redis:7-alpine",
    "rabbitmq:3.13-management-alpine",
]


def run(arguments, *, capture=False, check=True, **kwargs):
    return subprocess.run(
        arguments, check=check, text=True, capture_output=capture, **kwargs
    )


def eventually(function, timeout=300, interval=2, description="condition"):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = function()
        if value:
            return value
        time.sleep(interval)
    raise TimeoutError("Timed out waiting for " + description)


class Cluster(AbstractContextManager):
    def __init__(
        self, published=False, namespace="platform-smoke", reuse_test_images=False
    ):
        self.temporary = tempfile.TemporaryDirectory(prefix="dnk-platform-test-")
        self.work = Path(self.temporary.name)
        self.name = "dnk-test-" + uuid.uuid4().hex[:8]
        self.namespace = namespace
        self.environment = os.environ | {"KUBECONFIG": str(self.work / "kubeconfig")}
        self.published = published
        self.reuse_test_images = reuse_test_images
        self.created = False
        self.forwards = []
        self.images = [
            (
                f"ghcr.io/dinikon/runtime/{name}:latest"
                if published
                else f"dnk-test/{name}:helm-test"
            )
            for app in PUBLIC_IMAGES.values()
            for name in app.values()
        ]
        self.git_directory = self.work / "git"
        self.git_directory.mkdir()

    def __enter__(self):
        for executable in ["docker", KIND, "kubectl", HELM, "openssl", "curl"]:
            if shutil.which(executable) is None:
                raise RuntimeError(f"Required executable is unavailable: {executable}")
        if not self.published and not self.reuse_test_images:
            for dockerfile, cwd, image, target in [
                ("core/Dockerfile", ROOT, self.images[0], None),
                ("apps/core/Dockerfile", ROOT / "frontends", self.images[1], "runtime"),
                ("Dockerfile", ROOT, self.images[2], None),
                ("Dockerfile", ROOT / "frontends", self.images[3], None),
            ]:
                run(
                    [
                        "docker",
                        "build",
                        "-f",
                        dockerfile,
                        "-t",
                        image,
                        *(["--target", target] if target else []),
                        ".",
                    ],
                    cwd=cwd,
                )
        for image in self.images + INFRA_IMAGES:
            if run(
                ["docker", "image", "inspect", image], capture=True, check=False
            ).returncode:
                run(["docker", "pull", image])
        config = self.work / "kind.yaml"
        config.write_text(
            yaml.safe_dump(
                {
                    "kind": "Cluster",
                    "apiVersion": "kind.x-k8s.io/v1alpha4",
                    "nodes": [
                        {
                            "role": "control-plane",
                            "extraMounts": [
                                {
                                    "hostPath": str(self.git_directory),
                                    "containerPath": "/dnk-test-git",
                                }
                            ],
                        }
                    ],
                }
            )
        )
        self.created = True
        try:
            run(
                [
                    KIND,
                    "create",
                    "cluster",
                    "--name",
                    self.name,
                    "--image",
                    "kindest/node:v1.33.1",
                    "--config",
                    str(config),
                    "--kubeconfig",
                    self.environment["KUBECONFIG"],
                    "--wait",
                    "180s",
                ],
                env=self.environment,
            )
            # Docker's containerd store can retain a multiarch index with only the
            # host platform present. Export that platform explicitly for kind.
            architecture = run(
                ["docker", "info", "--format", "{{.Architecture}}"], capture=True
            ).stdout.strip()
            platform = "linux/" + {"aarch64": "arm64", "x86_64": "amd64"}.get(
                architecture, architecture
            )
            archive = self.work / "images.tar"
            run(
                [
                    "docker",
                    "image",
                    "save",
                    "--platform",
                    platform,
                    "-o",
                    str(archive),
                    *self.images,
                    *INFRA_IMAGES,
                ]
            )
            run(
                [KIND, "load", "image-archive", "--name", self.name, str(archive)],
                env=self.environment,
            )
            archive.unlink()
            self.kubectl("create", "namespace", self.namespace)
            return self
        except BaseException:
            self.__exit__(*__import__("sys").exc_info())
            raise

    def kubectl(self, *args, capture=False, check=True, namespace=None):
        return run(
            [
                "kubectl",
                "--context",
                "kind-" + self.name,
                "--namespace",
                namespace or self.namespace,
                *args,
            ],
            capture=capture,
            check=check,
            env=self.environment,
        )

    def get(self, kind, name=None, selector=None, namespace=None):
        args = [
            "get",
            kind,
            *([name] if name else []),
            *(["-l", selector] if selector else []),
            "-o",
            "json",
        ]
        result = self.kubectl(*args, capture=True, namespace=namespace)
        data = json.loads(result.stdout)
        return data if name else data["items"]

    def resources(self, kind, app=None, component=None):
        labels = []
        if app:
            labels.append(
                "app.kubernetes.io/name="
                + {"controlPlane": "dnk-control-plane", "runtime": "dnk-runtime-core"}[
                    app
                ]
            )
        if component:
            labels.append("app.kubernetes.io/component=" + component)
        return self.get(kind, selector=",".join(labels))

    def name_for(self, kind, app, component):
        items = self.resources(kind, app, component)
        if len(items) != 1:
            raise AssertionError(
                f"Expected one {app}/{component}/{kind}, found {len(items)}"
            )
        return items[0]["metadata"]["name"]

    def apply(self, name, resources, namespace=None):
        path = self.work / (name + ".yaml")
        path.write_text(yaml.safe_dump_all(resources))
        self.kubectl("apply", "-f", str(path), namespace=namespace)

    def values(self):
        values = platform_values()
        for app in PUBLIC_IMAGES:
            for component, image in PUBLIC_IMAGES[app].items():
                values[app].setdefault(component, {})["image"] = {
                    "repository": (
                        f"ghcr.io/dinikon/runtime/{image}"
                        if self.published
                        else f"dnk-test/{image}"
                    ),
                    "tag": "latest" if self.published else "helm-test",
                    "pullPolicy": "Never",
                }
            values[app]["backend"]["replicas"] = 2
            for dependency in ["postgresql", "redis"] + (
                ["rabbitmq"] if app == "runtime" else []
            ):
                values[app][dependency]["persistence"] = {"size": "256Mi"}
                values[app][dependency]["image"] = {"pullPolicy": "Never"}
        values["runtime"]["workers"] = {
            name: {"image": dict(values["runtime"]["backend"]["image"])}
            for name in ["publisher", "console"]
        }
        values["controlPlane"]["application"]["email"][
            "backend"
        ] = "django.core.mail.backends.locmem.EmailBackend"
        return values

    def rollout(self, timeout="600s"):
        for kind in ["statefulset", "deployment"]:
            for resource in self.get(kind):
                self.kubectl(
                    "rollout",
                    "status",
                    kind + "/" + resource["metadata"]["name"],
                    "--timeout=" + timeout,
                )

    def database(self, app, sql):
        # Infrastructure charts have shared component labels; match generated owner name.
        sts = next(
            r
            for r in self.get("statefulset")
            if r["metadata"]["name"].endswith(
                (
                    "control-plane-postgresql"
                    if app == "controlPlane"
                    else "runtime-postgresql"
                )
            )
        )
        env = {
            e["name"]: e.get("value")
            for e in sts["spec"]["template"]["spec"]["containers"][0]["env"]
        }
        return self.kubectl(
            "exec",
            "statefulset/" + sts["metadata"]["name"],
            "--",
            "psql",
            "-U",
            env["POSTGRES_USER"],
            "-d",
            env["POSTGRES_DB"],
            "-v",
            "ON_ERROR_STOP=1",
            "-At",
            "-c",
            sql,
            capture=True,
        ).stdout.strip()

    def redis(self, app, *arguments):
        suffix = "control-plane-redis" if app == "controlPlane" else "runtime-redis"
        statefulset = next(
            r for r in self.get("statefulset") if r["metadata"]["name"].endswith(suffix)
        )
        return self.kubectl(
            "exec",
            "statefulset/" + statefulset["metadata"]["name"],
            "--",
            "redis-cli",
            "-n",
            "1" if app == "controlPlane" else "0",
            *arguments,
            capture=True,
        ).stdout.strip()

    def rabbitmq(self, *arguments):
        statefulset = next(
            r
            for r in self.get("statefulset")
            if r["metadata"]["name"].endswith("runtime-rabbitmq")
        )
        return self.kubectl(
            "exec",
            "statefulset/" + statefulset["metadata"]["name"],
            "--",
            "rabbitmqctl",
            *arguments,
            capture=True,
        ).stdout.strip()

    def port_forward(self, target, remote_port, namespace=None):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        logfile = (self.work / f"forward-{port}.log").open("w")
        process = subprocess.Popen(
            [
                "kubectl",
                "--context",
                "kind-" + self.name,
                "--namespace",
                namespace or self.namespace,
                "port-forward",
                target,
                f"{port}:{remote_port}",
                "--address",
                "127.0.0.1",
            ],
            env=self.environment,
            stdout=logfile,
            stderr=logfile,
        )
        self.forwards.append((process, logfile))

        def connected():
            if process.poll() is not None:
                raise RuntimeError(f"Port forward exited: {target}")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=1):
                    return True
            except OSError:
                return False

        eventually(connected, timeout=30, description="port forward")
        return port

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type and self.created:
                for log in self.work.glob("forward-*.log"):
                    print(log.name + ": " + log.read_text(), flush=True)
                self.kubectl("get", "pods,jobs,pvc,events", check=False)
                for resource in self.get("pods"):
                    self.kubectl(
                        "logs",
                        resource["metadata"]["name"],
                        "--all-containers",
                        "--tail=70",
                        "--prefix=true",
                        check=False,
                    )
                if self.namespace == "argo-platform":
                    self.kubectl(
                        "get",
                        "applications",
                        "-o",
                        "yaml",
                        namespace="argocd",
                        check=False,
                    )
                    self.kubectl(
                        "logs",
                        "statefulset/argocd-application-controller",
                        "--tail=100",
                        namespace="argocd",
                        check=False,
                    )
        except (OSError, subprocess.SubprocessError) as diagnostic_error:
            print(
                "Could not collect all test diagnostics: " + str(diagnostic_error),
                flush=True,
            )
        finally:
            for process, logfile in self.forwards:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
                logfile.close()
            if self.created:
                run(
                    [KIND, "delete", "cluster", "--name", self.name],
                    env=self.environment,
                    check=False,
                )
            self.temporary.cleanup()
