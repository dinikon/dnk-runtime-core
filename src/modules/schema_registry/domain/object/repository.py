from typing import Protocol

from src.modules.schema_registry.domain.object.entity import ObjectEntity
from src.modules.shared import EntityIdVO


class ObjectRepositoryProtocol(Protocol):

    async def get_by_tenant_and_plural_name(
        self,
        *,
        tenant_id: EntityIdVO,
        plural_name: str,
    ) -> ObjectEntity | None: ...

    async def get_by_id(self, *, object_id: EntityIdVO) -> ObjectEntity | None: ...

    async def save(self, object_entity: ObjectEntity) -> None: ...

    async def list_by_tenant_id(
        self, *, tenant_id: EntityIdVO
    ) -> list[ObjectEntity]: ...

    async def replace_all_for_tenant(
        self,
        *,
        tenant_id: EntityIdVO,
        objects: list[ObjectEntity],
    ) -> None: ...

    async def reconcile_for_tenant(
        self,
        *,
        tenant_id: EntityIdVO,
        objects: list[ObjectEntity],
    ) -> None: ...
