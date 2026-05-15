from __future__ import annotations

from typing import Protocol

from src.modules.schema_registry.domain.relation.entity import RelationEntity
from src.modules.schema_registry.domain.relation.value_object import RuntimeRelationIdVO
from src.modules.shared import EntityIdVO


class RelationRepositoryProtocol(Protocol):
    """Порт persistence для runtime relation metadata."""

    async def get_by_id(
        self,
        *,
        relation_id: RuntimeRelationIdVO,
    ) -> RelationEntity | None:
        """Возвращает relation по id или None."""
        ...

    async def list_by_tenant_id(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> list[RelationEntity]:
        """Возвращает все relations tenant."""
        ...

    async def replace_all_for_tenant(
        self,
        *,
        tenant_id: EntityIdVO,
        relations: list[RelationEntity],
    ) -> None:
        """Полностью заменяет relation metadata tenant."""
        ...

    async def clear_for_tenant(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> None:
        """Удаляет всю relation metadata tenant."""
        ...

    async def reconcile_for_tenant(
        self,
        *,
        tenant_id: EntityIdVO,
        relations: list[RelationEntity],
    ) -> None:
        """Синхронизирует relation metadata tenant."""
        ...
