"""Authenticate management traffic before interpreting any proxy headers."""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import unquote

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send
from src.modules.control_plane.infrastructure.observability.metrics import (
    mtls_rejections,
)
from src.modules.shared.presentation.http.trusted_proxy import TrustedProxyHeaders


class ManagementTrustBoundary:
    def __init__(
        self,
        app: ASGIApp,
        *,
        enabled: bool,
        management_host: str,
        trusted_proxy_networks: list[str],
        allowed_core_fingerprints: list[str],
    ) -> None:
        self.app = app
        self.enabled = enabled
        self.management_host = management_host
        self.proxy_headers = TrustedProxyHeaders(trusted_proxy_networks)
        self.fingerprints = frozenset(allowed_core_fingerprints)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        scope = dict(scope)
        scope["state"] = dict(scope.get("state", {}))
        headers: dict[bytes, list[bytes]] = {}
        for key, value in scope.get("headers", []):
            headers.setdefault(key.lower(), []).append(value)
        host_values = headers.get(b"host", [])
        if len(host_values) != 1:
            await self._reject(scope, receive, send, 400)
            return
        raw_host = host_values[0].decode("latin-1").lower()
        raw_peer = scope.get("client")
        scope["state"]["socket_peer"] = raw_peer
        scope["state"]["control_plane_trusted"] = False
        trusted_peer = bool(raw_peer and self.proxy_headers.is_trusted(raw_peer[0]))
        internal = scope.get("path", "").split("/", 2)[1:2] == ["internal"]
        management = bool(self.management_host and raw_host == self.management_host)
        if internal:
            if not self.enabled or not management:
                await self._reject(scope, receive, send, 404)
                return
            if not trusted_peer or not self._certificate_allowed(headers):
                mtls_rejections.labels(reason="untrusted_connection").inc()
                await self._reject(scope, receive, send, 403)
                return
            scope["state"]["control_plane_trusted"] = True
        elif management:
            await self._reject(scope, receive, send, 404)
            return

        # Management policy checks the raw peer/certificate before normalization.
        self.proxy_headers.normalize(scope, headers, trusted_peer=trusted_peer)
        await self.app(scope, receive, send)

    def _certificate_allowed(self, headers: dict[bytes, list[bytes]]) -> bool:
        if headers.get(b"ssl-client-verify") != [b"SUCCESS"]:
            return False
        values = headers.get(b"ssl-client-cert", [])
        if len(values) != 1 or not 0 < len(values[0]) <= 16384:
            return False
        try:
            pem = unquote(values[0].decode("ascii")).encode("ascii")
            certificate = x509.load_pem_x509_certificate(pem)
            now = datetime.now(UTC)
            return (
                certificate.not_valid_before_utc
                <= now
                < certificate.not_valid_after_utc
                and certificate.fingerprint(hashes.SHA256()).hex() in self.fingerprints
            )
        except (ValueError, UnicodeError):
            return False

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send, code: int) -> None:
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
        else:
            await JSONResponse(
                {"detail": "Not found" if code == 404 else "Invalid connection"},
                status_code=code,
            )(scope, receive, send)
