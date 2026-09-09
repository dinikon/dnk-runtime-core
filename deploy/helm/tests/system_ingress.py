"""Real nginx/cert-manager fixtures, restricted to the caller's disposable kind.

The production issuer name is exercised against a private test CA. No ACME
orders, public DNS changes, or modifications to an existing cluster occur.
"""

import base64

from cluster import eventually, run

NGINX_VERSION = "controller-v1.13.3"
CERT_MANAGER_VERSION = "v1.18.2"


def setup_system_ingress(cluster):
    print("Installing test nginx Ingress and cert-manager controllers", flush=True)
    for name, url in [
        (
            "nginx-controller",
            f"https://raw.githubusercontent.com/kubernetes/ingress-nginx/{NGINX_VERSION}/deploy/static/provider/kind/deploy.yaml",
        ),
        (
            "cert-manager",
            f"https://github.com/cert-manager/cert-manager/releases/download/{CERT_MANAGER_VERSION}/cert-manager.yaml",
        ),
    ]:
        manifest = cluster.work / (name + ".yaml")
        run(
            [
                "curl",
                "--fail",
                "--location",
                "--silent",
                "--show-error",
                "--retry",
                "3",
                "--max-time",
                "120",
                url,
                "-o",
                str(manifest),
            ]
        )
        # Upstream installers contain resources in several namespaces. Preserve
        # their metadata.namespace while still pinning our private cluster context.
        run(
            [
                "kubectl",
                "--context",
                "kind-" + cluster.name,
                "apply",
                "--server-side",
                "-f",
                str(manifest),
            ],
            env=cluster.environment,
        )
    cluster.kubectl(
        "label",
        "node",
        cluster.name + "-control-plane",
        "ingress-ready=true",
        "--overwrite",
    )
    for namespace, deployments in [
        ("ingress-nginx", ["ingress-nginx-controller"]),
        (
            "cert-manager",
            ["cert-manager", "cert-manager-webhook", "cert-manager-cainjector"],
        ),
    ]:
        for deployment in deployments:
            cluster.kubectl(
                "rollout",
                "status",
                "deployment/" + deployment,
                "--timeout=300s",
                namespace=namespace,
            )

    # cert-manager issues real leaf certificates for the Ingress hosts, signed
    # by this private CA so the tests can verify TLS without public ACME/DNS.
    certificate = cluster.work / "ingress-test-ca.crt"
    key = cluster.work / "ingress-test-ca.key"
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
            "/CN=DNK disposable integration CA",
            "-addext",
            "basicConstraints=critical,CA:TRUE",
            "-addext",
            "keyUsage=critical,keyCertSign,cRLSign",
            "-keyout",
            str(key),
            "-out",
            str(certificate),
        ],
        capture=True,
    )
    cluster.apply(
        "test-ca",
        [
            {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": "dnk-test-ca"},
                "type": "kubernetes.io/tls",
                "data": {
                    "tls.crt": base64.b64encode(certificate.read_bytes()).decode(),
                    "tls.key": base64.b64encode(key.read_bytes()).decode(),
                },
            }
        ],
        namespace="cert-manager",
    )
    issuer = cluster.work / "test-issuer.yaml"
    issuer.write_text("""apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-production
spec:
  ca:
    secretName: dnk-test-ca
""")
    eventually(
        lambda: cluster.kubectl(
            "apply", "-f", str(issuer), check=False, capture=True
        ).returncode
        == 0,
        timeout=60,
        description="cert-manager admission webhook CA injection",
    )
    cluster.kubectl(
        "wait",
        "clusterissuer/letsencrypt-production",
        "--for=condition=Ready",
        "--timeout=90s",
    )
    return certificate


def certificate_endpoint(cluster, authority):
    ingresses = cluster.get("ingresses")
    assert len(ingresses) == 2
    for ingress in ingresses:
        name = ingress["spec"]["tls"][0]["secretName"]
        host = ingress["spec"]["rules"][0]["host"]
        eventually(
            lambda: cluster.kubectl(
                "get", "certificate/" + name, capture=True, check=False
            ).returncode
            == 0,
            timeout=60,
            description="ingress-shim certificate resource",
        )
        cluster.kubectl(
            "wait", "certificate/" + name, "--for=condition=Ready", "--timeout=120s"
        )
        certificate = cluster.get("certificate", name)
        assert certificate["spec"]["dnsNames"] == [host]
        assert certificate["spec"]["issuerRef"] == {
            "name": "letsencrypt-production",
            "kind": "ClusterIssuer",
            "group": "cert-manager.io",
        }
        secret = cluster.get("secret", name)
        assert secret["type"] == "kubernetes.io/tls"
        assert secret["data"].get("tls.crt") and secret["data"].get("tls.key")
        assert all(
            not route["backend"]["service"]["name"].endswith("-gateway")
            for route in ingress["spec"]["rules"][0]["http"]["paths"]
        )
    assert len(cluster.get("deployments")) == 5
    print(
        "PASS: both cert-manager certificates Ready; five app Deployments; direct Ingress routes",
        flush=True,
    )
    return {"certificate": authority, "resource": "service/ingress-nginx-controller"}
