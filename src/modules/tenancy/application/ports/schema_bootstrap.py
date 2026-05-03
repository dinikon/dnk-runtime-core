from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class TenantSchemaBootstrapContext:
    """Контекст bootstrap runtime-схемы tenant."""

    tenant_id: UUID
    schema_name: str
    seed_path: str


class TenantSchemaBootstrapPort(Protocol):
    """Порт bootstrap физической runtime-схемы tenant."""

    async def bootstrap(
        self,
        *,
        context: TenantSchemaBootstrapContext,
    ) -> None:
        """Создает или подготавливает runtime-схему tenant по контексту."""
        ...


class TenantSchemaBootstrapContextFactory:
    """Фабрика контекста bootstrap tenant schema из конфигурации."""

    def __init__(self, *, schema_prefix: str, default_seed_path: str) -> None:
        """Сохраняет префикс схемы и seed path по умолчанию."""
        self._schema_prefix = schema_prefix
        self._default_seed_path = default_seed_path

    def build(self, *, tenant_id: EntityIdVO) -> TenantSchemaBootstrapContext:
        """Создает bootstrap context с именем схемы на базе tenant UUID hex."""
        return TenantSchemaBootstrapContext(
            tenant_id=tenant_id.uuid,
            schema_name=f"{self._schema_prefix}{tenant_id.uuid.hex}",
            seed_path=self._default_seed_path,
        )


__all__ = [
    "TenantSchemaBootstrapContext",
    "TenantSchemaBootstrapContextFactory",
    "TenantSchemaBootstrapPort",
]
