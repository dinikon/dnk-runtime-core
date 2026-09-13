"""Disposable real-Core bridge for optional interoperability tests.

Default mode uses private process pipes and in-memory SQLite. Optional network
mode uses a temporary SQLite file and an HTTP upstream behind the caller's TLS
fixture. It never modifies the sibling checkout or its saved configuration.
"""

import base64
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
from urllib.parse import parse_qs, urlsplit

core = Path(sys.argv[1]).resolve()
sys.path[:0] = [str(core), str(core / "src")]
os.environ["DJANGO_SETTINGS_MODULE"] = "tests.settings"
import django

django.setup()
from django.conf import settings
from cryptography.fernet import Fernet

settings.ROOT_URLCONF = "dnk_core.urls"
settings.TENANT_SECRETS_ENCRYPTION_KEY = Fernet.generate_key().decode()
settings.PUBLIC_ORIGIN = os.environ.get(
    "CORE_INTEROP_PUBLIC_ORIGIN", "https://testserver"
).rstrip("/")
settings.MANAGEMENT_ORIGIN = os.environ.get(
    "CORE_INTEROP_MANAGEMENT_ORIGIN", "https://management.testserver"
)
settings.MANAGEMENT_TRUSTED_PROXIES = "127.0.0.1/32"
settings.ALLOWED_HOSTS = list(
    {
        *settings.ALLOWED_HOSTS,
        urlsplit(settings.PUBLIC_ORIGIN).hostname,
        urlsplit(settings.MANAGEMENT_ORIGIN).hostname,
    }
)
network_bind = os.environ.get("CORE_INTEROP_BIND")
sqlite_directory = (
    tempfile.TemporaryDirectory(prefix="dnk-core-interop-") if network_bind else None
)
if sqlite_directory:
    settings.DATABASES["default"]["NAME"] = str(
        Path(sqlite_directory.name) / "core.sqlite3"
    )
from django.core.management import call_command

call_command("migrate", verbosity=0, interactive=False)
from tests.test_tenant_oidc import TenantOIDCTests
from django.test import Client
from tenancy.models import TenantAccess, AccessEvent, InstanceCertificate, Tenant
from oidc.services import rotate_signing_key

TenantOIDCTests.setUpTestData()
data = TenantOIDCTests
client = Client()
control_token = secrets.token_urlsafe(32)
access_fixture_ids = set()
certificate_path = os.environ.get("CORE_INTEROP_RUNTIME_CERT")
if certificate_path:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes

    fingerprint = (
        x509.load_pem_x509_certificate(Path(certificate_path).read_bytes())
        .fingerprint(hashes.SHA256())
        .hex()
    )
    InstanceCertificate.objects.create(
        instance=data.instance, fingerprint=fingerprint, enabled=True
    )


def core_request(message, *, request_client=None):
    path = urlsplit(message["url"]).path
    query = urlsplit(message["url"]).query
    selected = request_client or client
    if message["action"] == "authorize":
        selected.force_login(data.owner if message["user"] == "owner" else data.guest)
        response = selected.get(path + ("?" + query if query else ""), secure=True)
    else:
        headers = {
            (
                "CONTENT_TYPE"
                if k.lower() == "content-type"
                else "HTTP_" + k.upper().replace("-", "_")
            ): v
            for k, v in message.get("headers", {}).items()
            if k.lower() not in {"content-length", "connection"}
        }
        response = selected.generic(
            message["method"],
            path + ("?" + query if query else ""),
            data=base64.b64decode(message.get("body", "")),
            secure=True,
            REMOTE_ADDR="127.0.0.1",
            **headers,
        )
    return response


def control(message):
    action = message["action"]
    if action == "access-fixture":
        tenant = Tenant.objects.create(
            name="Disposable access interoperability fixture",
            owner=data.owner,
            instance=data.instance,
            status=Tenant.Status.ACTIVE,
        )
        identifier = str(tenant.pk)
        access_fixture_ids.add(identifier)
        return {
            "tenant_id": identifier,
            "user_id": str(data.guest.pk),
            "instance_id": str(data.instance.pk),
        }
    if action == "remove-access-fixture":
        identifier = str(message["tenant_id"])
        if identifier not in access_fixture_ids:
            raise ValueError("This is not an owned access fixture")
        AccessEvent.objects.filter(tenant_id=identifier).delete()
        TenantAccess.objects.filter(tenant_id=identifier).delete()
        Tenant.objects.filter(pk=identifier).delete()
        access_fixture_ids.remove(identifier)
        return {"ok": True}
    if action == "access_count":
        return {"count": TenantAccess.objects.count()}
    if action == "access":
        record = TenantAccess.objects.filter(
            tenant_id=message["tenant_id"], user_id=message["user_id"]
        ).first()
        return {
            "exists": record is not None,
            "available": record.available if record else None,
            "version": record.version if record else None,
            "event_count": AccessEvent.objects.filter(
                tenant_id=message["tenant_id"], user_id=message["user_id"]
            ).count(),
        }
    if action == "register-certificate":
        tenant = Tenant.objects.get(pk=message["tenant_id"])
        InstanceCertificate.objects.update_or_create(
            fingerprint=message["fingerprint"],
            defaults={"instance": tenant.instance, "enabled": True},
        )
        return {"ok": True}
    if action == "rotate":
        rotate_signing_key(data.tenants[0].pk)
        return {"ok": True}
    if action == "login":
        client.force_login(data.owner if message["user"] == "owner" else data.guest)
        return {"cookies": {key: value.value for key, value in client.cookies.items()}}
    raise ValueError("Unknown test control action")


server = None
if network_bind:
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import threading

    class CoreHandler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.dispatch()

        def do_POST(self):
            self.dispatch()

        def do_PUT(self):
            self.dispatch()

        def dispatch(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if self.path.startswith("/__control__/"):
                if not secrets.compare_digest(
                    self.headers.get("X-Interop-Control-Token", ""), control_token
                ):
                    self.send_response(403)
                    self.end_headers()
                    return
                try:
                    parsed = urlsplit(self.path)
                    payload = {
                        k: values[0] for k, values in parse_qs(parsed.query).items()
                    }
                    if body:
                        payload.update(json.loads(body))
                    result = control(
                        {"action": parsed.path.rsplit("/", 1)[1], **payload}
                    )
                    encoded = json.dumps(result).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(encoded)))
                    self.end_headers()
                    self.wfile.write(encoded)
                except Exception:
                    self.send_response(400)
                    self.end_headers()
                return
            response = core_request(
                {
                    "action": "http",
                    "method": self.command,
                    "url": self.path,
                    "headers": dict(self.headers),
                    "body": base64.b64encode(body).decode(),
                },
                request_client=Client(),
            )
            self.send_response(response.status_code)
            for key, value in response.headers.items():
                self.send_header(key, value)
            for cookie in response.cookies.values():
                self.send_header("Set-Cookie", cookie.OutputString())
            self.end_headers()
            self.wfile.write(response.content)

    address, port = network_bind.rsplit(":", 1)
    server = HTTPServer((address, int(port)), CoreHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

print(
    json.dumps(
        {
            "credentials": data.credentials,
            "tenant_ids": [str(t.pk) for t in data.tenants],
            "owner": str(data.owner.pk),
            "guest": str(data.guest.pk),
            "instance_id": str(data.instance.pk),
            "control_token": control_token,
        }
    ),
    flush=True,
)
try:
    for line in sys.stdin:
        message = json.loads(line)
        try:
            if message["action"] in {"http", "authorize"}:
                response = core_request(message)
                result = {
                    "status": response.status_code,
                    "headers": dict(response.headers),
                    "body": base64.b64encode(response.content).decode(),
                }
            else:
                result = control(message)
            print(json.dumps(result), flush=True)
        except Exception as exc:
            print(json.dumps({"bridge_error": type(exc).__name__}), flush=True)
finally:
    if server:
        server.shutdown()
        server.server_close()
    if sqlite_directory:
        sqlite_directory.cleanup()
