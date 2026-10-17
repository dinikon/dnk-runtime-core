"""Normalize proxy headers only after the caller has authenticated the raw peer."""

import ipaddress
from starlette.types import Scope


class TrustedProxyHeaders:
    """Проверяет адрес ingress и нормализует переданные им HTTP-заголовки."""

    def __init__(self, networks: list[str]) -> None:
        self.networks = tuple(
            ipaddress.ip_network(value, strict=False) for value in networks
        )

    def is_trusted(self, address: str) -> bool:
        try:
            parsed = ipaddress.ip_address(address)
            return any(parsed in network for network in self.networks)
        except ValueError:
            return False

    def normalize(
        self, scope: Scope, headers: dict[bytes, list[bytes]], *, trusted_peer: bool
    ) -> None:
        """Читает только заголовки доверенного ingress, затем удаляет служебные поля."""
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
                    if not self.is_trusted(address):
                        break
        scope["headers"] = [
            (key, value)
            for key, value in scope.get("headers", [])
            if not key.lower().startswith((b"x-forwarded-", b"ssl-client-"))
            and key.lower() != b"forwarded"
        ]
