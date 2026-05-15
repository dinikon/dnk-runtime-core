from __future__ import annotations

from typing import Protocol

from src.modules.schema_registry.domain.relation.entity import RelationEntity
from src.modules.schema_registry.domain.relation.value_object import RuntimeRelationIdVO
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
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

    async def list_by_object_id(
        self,
        *,
        tenant_id: EntityIdVO,
        object_id: RuntimeObjectIdVO,
    ) -> list[RelationEntity]:
        """Возвращает relations tenant, где object является source или target."""
        ...

    async def get_by_tenant_and_name(
        self,
        *,
        tenant_id: EntityIdVO,
        name: str,
    ) -> RelationEntity | None:
        """Возвращает relation по tenant/name или None."""
        ...

    async def add(self, relation: RelationEntity) -> None:
        """Добавляет одну relation metadata."""
        ...

    async def delete(
        self,
        *,
        tenant_id: EntityIdVO,
        relation_id: RuntimeRelationIdVO,
    ) -> None:
        """Удаляет одну relation metadata."""
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
