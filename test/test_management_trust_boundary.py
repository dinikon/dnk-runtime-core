from datetime import UTC, datetime, timedelta
import logging
import unittest
from urllib.parse import quote

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from starlette.responses import JSONResponse
from starlette.requests import Request

from src.modules.shared.presentation.http.host import extract_request_host

from src.modules.shared.presentation.http.trust_boundary import (
    ManagementTrustBoundary,
    RedactAccessQuery,
)


class HostAuthorityTests(unittest.TestCase):
    def test_invalid_authorities_cannot_resolve_a_tenant_from_url_components(self):
        for host in (
            "userinfo@tenant.example.test",
            "tenant.example.test/other",
            "tenant.example.test?query",
            "tenant.example.test#fragment",
            "tenant.example.test:bad",
            "tenant.example.test:65536",
            "tenant.example.test.",
            "tenant..example.test",
        ):
            request = Request(
                {
                    "type": "http",
                    "scheme": "https",
                    "path": "/",
                    "headers": [(b"host", host.encode())],
                }
            )
            self.assertEqual(extract_request_host(request), "", host)

    def test_host_is_case_insensitive_and_forwarded_host_is_ignored(self):
        request = Request(
            {
                "type": "http",
                "scheme": "https",
                "path": "/",
                "headers": [
                    (b"host", b"TENANT.example.test:443"),
                    (b"x-forwarded-host", b"other.example.test"),
                ],
            }
        )
        self.assertEqual(extract_request_host(request), "tenant.example.test")


class ManagementTrustTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Core test")])
        now = datetime.now(UTC)
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(hours=1))
            .sign(key, hashes.SHA256())
        )
        cls.fingerprint = cert.fingerprint(hashes.SHA256()).hex()
        cls.pem = quote(cert.public_bytes(serialization.Encoding.PEM).decode())

    async def request(
        self,
        *,
        peer="10.1.1.2",
        host="manage.runtime.test",
        path="/internal/v1/status/",
        extra=None,
    ):
        async def endpoint(scope, receive, send):
            await JSONResponse(
                {
                    "trusted": scope["state"]["control_plane_trusted"],
                    "peer": scope["state"]["socket_peer"][0],
                    "client": scope["client"][0],
                    "scheme": scope["scheme"],
                    "headers": dict(
                        (k.decode(), v.decode()) for k, v in scope["headers"]
                    ),
                }
            )(scope, receive, send)

        app = ManagementTrustBoundary(
            endpoint,
            enabled=True,
            management_host="manage.runtime.test",
            trusted_proxy_networks=["10.1.0.0/16"],
            allowed_core_fingerprints=[self.fingerprint],
        )
        headers = {"ssl-client-verify": "SUCCESS", "ssl-client-cert": self.pem}
        headers.update(extra or {})
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=(peer, 1234)),
            base_url=f"http://{host}",
        ) as client:
            return await client.get(path, headers=headers)

    async def test_ingress_certificate_and_raw_peer_are_required(self):
        self.assertEqual((await self.request()).status_code, 200)
        self.assertEqual((await self.request(peer="192.0.2.1")).status_code, 403)
        self.assertEqual(
            (await self.request(extra={"ssl-client-verify": "NONE"})).status_code, 403
        )
        self.assertEqual(
            (await self.request(extra={"ssl-client-cert": "invalid"})).status_code, 403
        )
        self.assertEqual(
            (await self.request(extra={"ssl-client-cert": "x" * 17000})).status_code,
            403,
        )

    async def test_hosts_cannot_cross_management_boundary(self):
        self.assertEqual(
            (await self.request(host="tenant.runtime.test")).status_code, 404
        )
        self.assertEqual(
            (await self.request(path="/api/console/auth/me")).status_code, 404
        )

    async def test_forwarded_headers_never_authorize_socket_peer(self):
        result = await self.request(
            peer="192.0.2.1", extra={"x-forwarded-for": "10.1.1.2"}
        )
        self.assertEqual(result.status_code, 403)

    async def test_trusted_proxy_chain_is_read_from_right_and_headers_removed(self):
        result = await self.request(
            extra={
                "x-forwarded-for": "1.2.3.4, 192.0.2.7, 10.1.1.1",
                "x-forwarded-proto": "https",
            }
        )
        self.assertEqual(result.json()["peer"], "10.1.1.2")
        self.assertEqual(result.json()["client"], "192.0.2.7")
        self.assertEqual(result.json()["scheme"], "https")
        self.assertNotIn("ssl-client-cert", result.json()["headers"])

    async def test_public_request_does_not_trust_spoofed_proxy_headers(self):
        result = await self.request(
            peer="192.0.2.1",
            host="tenant.runtime.test",
            path="/api/console/auth/me",
            extra={
                "x-forwarded-for": "10.1.1.2",
                "x-forwarded-host": "manage.runtime.test",
                "x-forwarded-proto": "https",
            },
        )
        self.assertFalse(result.json()["trusted"])
        self.assertEqual(result.json()["client"], "192.0.2.1")
        self.assertEqual(result.json()["scheme"], "http")
        self.assertNotIn("x-forwarded-host", result.json()["headers"])

    def test_access_log_removes_sensitive_query(self):
        record = logging.LogRecord(
            "uvicorn.access",
            logging.INFO,
            "",
            0,
            "%s %s %s %s %s",
            (
                "peer",
                "GET",
                "/api/auth/cloud/callback/?code=secret&state=secret",
                "1.1",
                303,
            ),
            None,
        )
        RedactAccessQuery().filter(record)
        self.assertNotIn("secret", record.getMessage())
