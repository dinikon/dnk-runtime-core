"""Authenticate management traffic before interpreting any proxy headers."""

from __future__ import annotations

import ipaddress
import logging
from datetime import UTC, datetime
from urllib.parse import unquote

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send
from src.modules.shared.infrastructure.observability.metrics import mtls_rejections


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
        self.networks = tuple(
            ipaddress.ip_network(value, strict=False)
            for value in trusted_proxy_networks
        )
        self.fingerprints = frozenset(allowed_core_fingerprints)

    def _trusted(self, address: str) -> bool:
        try:
            parsed = ipaddress.ip_address(address)
            return any(parsed in network for network in self.networks)
        except ValueError:
            return False

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
        trusted_peer = bool(raw_peer and self._trusted(raw_peer[0]))
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

        # Read only a trusted ingress's values, after authenticating its raw peer.
        if trusted_peer:
            proto = headers.get(b"x-forwarded-proto", [])
            if len(proto) == 1 and proto[0] in {b"http", b"https"}:
                scope["scheme"] = proto[0].decode("ascii")
            forwarded = headers.get(b"x-forwarded-for", [])
            if len(forwarded) == 1:
                chain = forwarded[0].decode("latin-1").split(",")
                for item in reversed(chain):
                    address = item.strip()
                    try:
                        ipaddress.ip_address(address)
                    except ValueError:
                        break
                    scope["client"] = (address, 0)
                    if not self._trusted(address):
                        break
        # No downstream helper can accidentally trust client-supplied headers.
        scope["headers"] = [
            (key, value)
            for key, value in scope.get("headers", [])
            if not key.lower().startswith((b"x-forwarded-", b"ssl-client-"))
            and key.lower() != b"forwarded"
        ]
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


class RedactAccessQuery(logging.Filter):
    """Do not retain authorization codes or invitation tokens in access logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and len(record.args) == 5:
            args = list(record.args)
            if isinstance(args[2], str):
                args[2] = args[2].split("?", 1)[0]
                record.args = tuple(args)
        return True


def install_access_log_redaction() -> None:
    logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(item, RedactAccessQuery) for item in logger.filters):
        logger.addFilter(RedactAccessQuery())
