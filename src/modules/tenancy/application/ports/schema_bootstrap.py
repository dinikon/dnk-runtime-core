from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TenantSchemaBootstrapContext:
    tenant_id: UUID
    schema_name: str
    seed_path: str


class TenantSchemaBootstrapPort(Protocol):
    async def bootstrap(
        self,
        *,
        context: TenantSchemaBootstrapContext,
    ) -> None: ...


class TenantSchemaBootstrapContextFactory:
    def __init__(self, *, schema_prefix: str, default_seed_path: str) -> None:
        self._schema_prefix = schema_prefix
        self._default_seed_path = default_seed_path

    def build(self, *, tenant_id: UUID) -> TenantSchemaBootstrapContext:
        return TenantSchemaBootstrapContext(
            tenant_id=tenant_id,
            schema_name=f"{self._schema_prefix}{tenant_id.hex}",
            seed_path=self._default_seed_path,
        )


__all__ = [
    "TenantSchemaBootstrapContext",
    "TenantSchemaBootstrapContextFactory",
    "TenantSchemaBootstrapPort",
]
