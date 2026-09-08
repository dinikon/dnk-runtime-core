from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.modules.shared import EntityIdVO
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)


@dataclass(frozen=True, slots=True)
class TenantSchemaBootstrapContext:
    """Контекст создания tenant-схемы и применения статических миграций."""

    tenant_id: UUID
    schema_name: str


class TenantSchemaBootstrapPort(Protocol):
    """Порт создания физической tenant-схемы и применения миграций."""

    async def bootstrap(
        self,
        *,
        context: TenantSchemaBootstrapContext,
    ) -> None:
        """Создает или подготавливает tenant-схему tenant по контексту."""
        ...


class TenantSchemaBootstrapContextFactory:
    """Фабрика контекста bootstrap tenant schema из конфигурации."""

    def __init__(self, *, schema_prefix: str) -> None:
        """Сохраняет общую стратегию именования схем."""
        self._naming = TenantSchemaNaming(schema_prefix)

    def build(self, *, tenant_id: EntityIdVO) -> TenantSchemaBootstrapContext:
        """Создает bootstrap context с именем схемы на базе tenant UUID hex."""
        return TenantSchemaBootstrapContext(
            tenant_id=tenant_id.uuid,
            schema_name=self._naming.schema_name(tenant_id),
        )


__all__ = [
    "TenantSchemaBootstrapContext",
    "TenantSchemaBootstrapContextFactory",
    "TenantSchemaBootstrapPort",
]
