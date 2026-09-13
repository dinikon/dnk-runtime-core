import json
import os
from pathlib import Path
from datetime import datetime, timedelta, UTC
from uuid import uuid4
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.fernet import Fernet

root = Path(os.environ["DNK_HTTPS_FIXTURE_DIRECTORY"])
from sqlalchemy.engine import make_url
from urllib.parse import urlsplit, unquote

database_url = make_url(os.environ["DNK_TEST_DATABASE_URL"])
redis_url = urlsplit(os.environ["DNK_TEST_REDIS_URL"])
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "DNK local integration CA")])
now = datetime.now(UTC)
ca = (
    x509.CertificateBuilder()
    .subject_name(name)
    .issuer_name(name)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(now - timedelta(days=1))
    .not_valid_after(now + timedelta(days=30))
    .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
    .add_extension(
        x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False
    )
    .add_extension(
        x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()),
        critical=False,
    )
    .add_extension(
        x509.KeyUsage(True, False, False, False, False, True, True, False, False),
        critical=True,
    )
    .sign(key, hashes.SHA256())
)
(root / "ca.crt").write_bytes(ca.public_bytes(serialization.Encoding.PEM))


def leaf(label, client=False):
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    n = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, label)])
    builder = (
        x509.CertificateBuilder()
        .subject_name(n)
        .issuer_name(ca.subject)
        .public_key(k.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=7))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(k.public_key()), critical=False
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.KeyUsage(True, False, True, False, False, False, False, False, False),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage(
                [
                    (
                        ExtendedKeyUsageOID.CLIENT_AUTH
                        if client
                        else ExtendedKeyUsageOID.SERVER_AUTH
                    )
                ]
            ),
            critical=False,
        )
    )
    if not client:
        builder = builder.add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName(h)
                    for h in [
                        "*.first.example.test",
                        "*.second.example.test",
                        "runtime-management.example.test",
                        "core.example.test",
                        "core-management.example.test",
                    ]
                ]
            ),
            critical=False,
        )
    cert = builder.sign(key, hashes.SHA256())
    (root / (label + ".crt")).write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    path = root / (label + ".key")
    path.write_bytes(
        k.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    path.chmod(0o600)
    return cert.fingerprint(hashes.SHA256()).hex()


leaf("server")
fingerprints = {
    label: leaf(label, True) for label in ["core", "core-rotated", "foreign", "runtime"]
}
if not (root / "encryption.key").exists():
    (root / "encryption.key").write_bytes(Fernet.generate_key())
    (root / "encryption.key").chmod(0o600)
instance = (
    json.loads((root / "fixture.json").read_text())["instance_id"]
    if (root / "fixture.json").exists()
    else str(uuid4())
)
env = {
    "DB_HOST": database_url.host,
    "DB_PORT": str(database_url.port or 5432),
    "DB_USERNAME": database_url.username,
    "DB_PASSWORD": database_url.password,
    "DB_DATABASE": os.environ["DNK_HTTPS_DATABASE_NAME"],
    "SQLALCHEMY_ECHO": "false",
    "DEPLOY_ENV": "TEST",
    "PROJECT__VERSION": "integration-v1",
    "REDIS_HOST": redis_url.hostname,
    "REDIS_PORT": str(redis_url.port or 6379),
    "REDIS_USERNAME": unquote(redis_url.username or ""),
    "REDIS_PASSWORD": unquote(redis_url.password or ""),
    "REDIS_DB": redis_url.path.lstrip("/") or "0",
    "REDIS_USE_SSL": str(redis_url.scheme == "rediss").lower(),
    "RABBITMQ__ENABLED": "false",
    "EMAIL__SMTP__HOST": "127.0.0.1",
    "EMAIL__SMTP__PORT": "1025",
    "EMAIL__SMTP__USERNAME": "",
    "EMAIL__SMTP__PASSWORD": "",
    "EMAIL__SMTP__USE_STARTTLS": "false",
    "EMAIL__SMTP__USE_TLS": "false",
    "CONTROL_PLANE__ENABLED": "true",
    "CONTROL_PLANE__PUBLIC_ORIGIN": "https://core.example.test",
    "CONTROL_PLANE__MANAGEMENT_ORIGIN": "https://core-management.example.test",
    "CONTROL_PLANE__MANAGEMENT_HOST": "runtime-management.example.test",
    "CONTROL_PLANE__INSTANCE_ID": str(instance),
    "CONTROL_PLANE__ALLOWED_BASE_DOMAINS": json.dumps(
        ["first.example.test", "second.example.test", "missing.example.test"]
    ),
    "CONTROL_PLANE__TRUSTED_PROXY_NETWORKS": os.environ["DNK_HTTPS_TRUSTED_PEERS"],
    "CONTROL_PLANE__ALLOWED_CORE_FINGERPRINTS": json.dumps(
        [fingerprints["core"], fingerprints["core-rotated"]]
    ),
    "CONTROL_PLANE__ENCRYPTION_KEY_PATH": str(root / "encryption.key"),
    "CONTROL_PLANE__SECRET_ENCRYPTION_KEY": "",
    "CONTROL_PLANE__CLIENT_CERT_PATH": str(root / "runtime.crt"),
    "CONTROL_PLANE__CLIENT_KEY_PATH": str(root / "runtime.key"),
    "CONTROL_PLANE__CA_BUNDLE_PATH": str(root / "ca.crt"),
    "CONTROL_PLANE__INGRESS_PROBE_ADDRESS": "127.0.0.1:" + os.environ["DNK_HTTPS_PORT"],
    "CONTROL_PLANE__RABBITMQ_URL": os.environ["DNK_TEST_RABBITMQ_URL"],
    "CONTROL_PLANE__INSTALL_QUEUE": "dnk.https."
    + os.environ["DNK_HTTPS_DATABASE_NAME"]
    + ".installation",
    "CONTROL_PLANE__ACCESS_QUEUE": "dnk.https."
    + os.environ["DNK_HTTPS_DATABASE_NAME"]
    + ".access",
    "SSL_CERT_FILE": str(root / "ca.crt"),
}
(root / "environment.json").write_text(json.dumps(env, indent=2))
(root / "environment.json").chmod(0o600)
(root / "fixture.json").write_text(
    json.dumps(
        {
            "instance_id": str(instance),
            "fingerprints": fingerprints,
            "database": env["DB_DATABASE"],
            "runtime_port": int(os.environ["DNK_HTTPS_API_PORT"]),
            "core_port": 18090,
            "https_ports": [int(os.environ["DNK_HTTPS_PORT"])],
        },
        indent=2,
    )
)
config = """events {}
http {
 access_log off;
 error_log /dev/stderr crit;
 ssl_certificate /fixture/server.crt;
 ssl_certificate_key /fixture/server.key;
 proxy_set_header Host $host;
 proxy_set_header X-Forwarded-Proto https;
 proxy_set_header X-Forwarded-For $remote_addr;
 server { listen 443 ssl default_server; server_name _; return 404; }
 server {
  listen 443 ssl; server_name runtime-management.example.test;
  ssl_client_certificate /fixture/ca.crt;
  ssl_verify_client on;
  location /internal/v1/ {
   proxy_pass http://host.docker.internal:18089;
   proxy_set_header Host $host;
   proxy_set_header ssl-client-verify $ssl_client_verify;
   proxy_set_header ssl-client-cert $ssl_client_escaped_cert;
  }
  location / { return 404; }
 }
 server {
  listen 443 ssl; server_name *.first.example.test *.second.example.test *.missing.example.test;
  proxy_set_header Host $host;
  proxy_set_header X-Forwarded-Proto https;
  proxy_set_header X-Forwarded-For $remote_addr;
  proxy_set_header ssl-client-verify "";
  proxy_set_header ssl-client-cert "";
  location /internal/ { return 404; }
  location / { proxy_pass http://host.docker.internal:18089; }
 }
 server {
  listen 443 ssl; server_name core.example.test;
  location / { proxy_pass http://host.docker.internal:18090; }
 }
 server {
  listen 443 ssl; server_name core-management.example.test;
  ssl_client_certificate /fixture/ca.crt;
  ssl_verify_client on;
  location / {
   proxy_pass http://host.docker.internal:18090;
   proxy_set_header Host $host;
   proxy_set_header ssl-client-verify $ssl_client_verify;
   proxy_set_header ssl-client-cert $ssl_client_escaped_cert;
   proxy_set_header ssl-client-fingerprint $ssl_client_fingerprint;
  }
 }
}
"""
(root / "nginx.conf").write_text(
    config.replace(":18089", ":" + os.environ["DNK_HTTPS_API_PORT"])
)
print("Prepared local integration certificates, settings and nginx config.")
