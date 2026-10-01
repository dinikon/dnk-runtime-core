from typing import Protocol
from src.modules.identity.application.cloud.port.cloud import CloudConnection


class OidcClientPort(Protocol):

    async def authorization_url(
        self, connection: CloudConnection, *, state: str, nonce: str, verifier: str
    ) -> str: ...

    async def exchange(
        self, connection: CloudConnection, *, code: str, nonce: str, verifier: str
    ) -> str: ...
