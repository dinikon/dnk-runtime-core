from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class CloudConnection:
    core_tenant_id: UUID
    issuer: str
    client_id: str
    client_secret: str = field(repr=False)
    callback: str


class CloudConnectionReaderPort(Protocol):
    async def get(self, tenant_id: UUID) -> CloudConnection | None: ...


class AccessProjectionWriterPort(Protocol):
    async def set_available(
        self,
        tenant_id: UUID,
        global_user_id: UUID,
        available: bool,
        role: str | None = None,
    ) -> int: ...
