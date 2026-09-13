"""Enforce the rendered Helm backend policy in a disposable kind/Calico cluster.

Requires Docker, kubectl, Helm and kind. Images and the official Calico manifest
are downloaded unless cached/provided. Never uses the user's Kubernetes context.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

import yaml

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_NAMESPACE = "runtime-policy-test"
INGRESS_NAMESPACE = "ingress-nginx"
OUTSIDER_NAMESPACE = "outsider-policy-test"
CLIENTS = (
    (INGRESS_NAMESPACE, "allowed-controller", "controller"),
    (RUNTIME_NAMESPACE, "same-namespace", "client"),
    (OUTSIDER_NAMESPACE, "foreign-namespace", "controller"),
    (INGRESS_NAMESPACE, "wrong-controller-label", "client"),
)


def run(arguments, **kwargs):
    return subprocess.run(
        [str(value) for value in arguments],
        text=True,
        capture_output=True,
        check=True,
        timeout=600,
        **kwargs,
    ).stdout


def policy_manifest(directory, helm):
    # Use the same complete values fixture as the chart contract tests; never
    # reproduce policy rules here, so changes to the actual chart are exercised.
    sys.path.insert(0, str(ROOT / "helm/tests"))
    from test_control_plane_deployment import integrated_values

    values = directory / "values.yaml"
    values.write_text(yaml.safe_dump(integrated_values()))
    rendered = run([helm, "template", "contract", ROOT / "helm", "-f", values])
    policy = next(
        value
        for value in yaml.safe_load_all(rendered)
        if value
        and value["kind"] == "NetworkPolicy"
        and value["metadata"]["name"].endswith("-backend-ingress")
    )
    policy["metadata"]["namespace"] = RUNTIME_NAMESPACE
    return policy


def fixtures(policy, image):
    labels = policy["spec"]["podSelector"]["matchLabels"]
    objects = [
        {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": namespace}}
        for namespace in (RUNTIME_NAMESPACE, INGRESS_NAMESPACE, OUTSIDER_NAMESPACE)
    ]
    objects += [
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "backend-nginx", "namespace": RUNTIME_NAMESPACE},
            "data": {
                "default.conf": 'server { listen 8000; location / { return 200 "reachable\\n"; } }'
            },
        },
        {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "backend",
                "namespace": RUNTIME_NAMESPACE,
                "labels": labels,
            },
            "spec": {
                "containers": [
                    {
                        "name": "backend",
                        "image": image,
                        "imagePullPolicy": "IfNotPresent",
                        "ports": [{"containerPort": 8000}],
                        "volumeMounts": [
                            {
                                "name": "config",
                                "mountPath": "/etc/nginx/conf.d/default.conf",
                                "subPath": "default.conf",
                            }
                        ],
                    }
                ],
                "volumes": [{"name": "config", "configMap": {"name": "backend-nginx"}}],
            },
        },
        {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": "backend", "namespace": RUNTIME_NAMESPACE},
            "spec": {
                "selector": labels,
                "ports": [{"port": 8000, "targetPort": 8000}],
            },
        },
    ]
    for namespace, name, component in CLIENTS:
        objects.append(
            {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {
                    "name": name,
                    "namespace": namespace,
                    "labels": {"app.kubernetes.io/component": component},
                },
                "spec": {
                    "containers": [
                        {
                            "name": "client",
                            "image": image,
                            "imagePullPolicy": "IfNotPresent",
                            "command": ["sh", "-c", "sleep 3600"],
                        }
                    ]
                },
            }
        )
    return objects


def check_reachability(kubectl):
    pod_ip = run(
        kubectl
        + [
            "get",
            "pod",
            "backend",
            "-n",
            RUNTIME_NAMESPACE,
            "-o",
            "jsonpath={.status.podIP}",
        ]
    )
    routes = {
        "pod_ip": f"http://{pod_ip}:8000/",
        "service": f"http://backend.{RUNTIME_NAMESPACE}.svc.cluster.local:8000/",
    }

    def check(item):
        namespace, pod, route, url = item
        result = subprocess.run(
            kubectl
            + ["exec", "-n", namespace, pod, "--", "wget", "-T", "3", "-qO-", url],
            text=True,
            capture_output=True,
            timeout=15,
        )
        return {
            "namespace": namespace,
            "pod": pod,
            "route": route,
            "allowed": result.returncode == 0 and result.stdout.strip() == "reachable",
            "exit_code": result.returncode,
            "error": result.stderr.strip(),
        }

    with ThreadPoolExecutor(max_workers=8) as executor:
        return list(
            executor.map(
                check,
                [
                    (namespace, pod, route, url)
                    for namespace, pod, _ in CLIENTS
                    for route, url in routes.items()
                ],
            )
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", default="kind", help="Path to kind executable")
    parser.add_argument("--kubectl", default="kubectl")
    parser.add_argument("--helm", default="helm")
    parser.add_argument("--node-image", default="kindest/node:v1.33.1")
    parser.add_argument("--nginx-image", default="nginx:1.27-alpine")
    parser.add_argument(
        "--calico-manifest",
        default="https://raw.githubusercontent.com/projectcalico/calico/v3.30.0/manifests/calico.yaml",
        help="Official Calico manifest URL or previously downloaded file",
    )
    parser.add_argument("--output", type=Path, help="Save non-secret verification JSON")
    args = parser.parse_args()
    name = "dnk-policy-" + uuid4().hex[:12]
    with tempfile.TemporaryDirectory(prefix="dnk-runtime-policy-") as temporary:
        directory = Path(temporary)
        config = directory / "kind.yaml"
        config.write_text(
            yaml.safe_dump(
                {
                    "kind": "Cluster",
                    "apiVersion": "kind.x-k8s.io/v1alpha4",
                    "networking": {
                        "disableDefaultCNI": True,
                        "podSubnet": "192.168.0.0/16",
                    },
                    "nodes": [{"role": "control-plane"}],
                }
            )
        )
        policy = policy_manifest(directory, args.helm)
        kubectl = [
            args.kubectl,
            "--kubeconfig",
            str(directory / "kubeconfig"),
            "--context",
            "kind-" + name,
        ]
        try:
            print("Creating disposable kind/Calico cluster", flush=True)
            run(
                [
                    args.kind,
                    "create",
                    "cluster",
                    "--name",
                    name,
                    "--image",
                    args.node_image,
                    "--config",
                    config,
                    "--kubeconfig",
                    directory / "kubeconfig",
                    "--wait",
                    "0s",
                ]
            )
            run(kubectl + ["apply", "-f", args.calico_manifest])
            run(
                kubectl
                + [
                    "rollout",
                    "status",
                    "daemonset/calico-node",
                    "-n",
                    "kube-system",
                    "--timeout=300s",
                ]
            )
            run(
                kubectl
                + ["wait", "nodes", "--all", "--for=condition=Ready", "--timeout=300s"]
            )
            fixture_file = directory / "fixtures.yaml"
            fixture_file.write_text(
                yaml.safe_dump_all(fixtures(policy, args.nginx_image))
            )
            run(kubectl + ["apply", "-f", fixture_file])
            for namespace in (RUNTIME_NAMESPACE, INGRESS_NAMESPACE, OUTSIDER_NAMESPACE):
                run(
                    kubectl
                    + [
                        "wait",
                        "pods",
                        "--all",
                        "-n",
                        namespace,
                        "--for=condition=Ready",
                        "--timeout=300s",
                    ]
                )
            before = check_reachability(kubectl)
            if not all(item["allowed"] for item in before):
                raise AssertionError({"baseline_failed": before})
            print(
                "All sources reachable before policy; checking enforcement", flush=True
            )
            policy_file = directory / "policy.yaml"
            policy_file.write_text(yaml.safe_dump(policy))
            run(kubectl + ["apply", "-f", policy_file])
            for _ in range(6):
                after = check_reachability(kubectl)
                if all(
                    item["allowed"] == (item["pod"] == "allowed-controller")
                    for item in after
                ):
                    break
                time.sleep(2)
            else:
                raise AssertionError({"policy_not_enforced": after})
            if not all(
                "timed out" in item["error"] for item in after if not item["allowed"]
            ):
                raise AssertionError({"unexpected_denial_error": after})
            result = {
                "kind": run([args.kind, "version"]).strip(),
                "kubernetes_node_image": args.node_image,
                "calico_manifest": args.calico_manifest,
                "policy": policy,
                "before": before,
                "after": after,
            }
            if args.output:
                args.output.write_text(json.dumps(result, indent=2) + "\n")
            print(
                "PASS: ingress controller allowed; same namespace, wrong namespace and wrong controller label denied via Pod IP and Service",
                flush=True,
            )
        finally:
            # The random name and dedicated kubeconfig ensure no existing/user
            # cluster or context is touched, including after partial setup failure.
            run(
                [
                    args.kind,
                    "delete",
                    "cluster",
                    "--name",
                    name,
                    "--kubeconfig",
                    directory / "kubeconfig",
                ]
            )
            print("Removed only the disposable policy test cluster", flush=True)


if __name__ == "__main__":
    main()
