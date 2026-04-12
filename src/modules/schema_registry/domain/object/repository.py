from typing import Protocol

from src.modules.schema_registry.domain.object.entity import ObjectEntity
from src.modules.shared import EntityIdVO


class ObjectRepositoryProtocol(Protocol):
    """Порт хранения runtime object metadata и связанных полей."""

    async def get_by_tenant_and_singular_name(
        self,
        *,
        tenant_id: EntityIdVO,
        singular_name: str,
    ) -> ObjectEntity | None:
        """Возвращает объект tenant по singular-имени или None."""
        ...

    async def get_by_tenant_and_plural_name(
        self,
        *,
        tenant_id: EntityIdVO,
        plural_name: str,
    ) -> ObjectEntity | None:
        """Возвращает объект tenant по plural-имени или None."""
        ...

    async def get_by_id(self, *, object_id: EntityIdVO) -> ObjectEntity | None:
        """Возвращает объект по id или None."""
        ...

    async def save(self, object_entity: ObjectEntity) -> None:
        """Сохраняет один runtime-объект и его поля."""
        ...

    async def list_by_tenant_id(
        self, *, tenant_id: EntityIdVO
    ) -> list[ObjectEntity]:
        """Возвращает все runtime-объекты tenant."""
        ...

    async def replace_all_for_tenant(
        self,
        *,
        tenant_id: EntityIdVO,
        objects: list[ObjectEntity],
    ) -> None:
        """Полностью заменяет набор объектов tenant."""
        ...

    async def reconcile_for_tenant(
        self,
        *,
        tenant_id: EntityIdVO,
        objects: list[ObjectEntity],
    ) -> None:
        """Синхронизирует набор объектов tenant без полной пересоздачи metadata."""
        ...
