from typing import Protocol

from modules.schema_registry.domain.object.entity import ObjectEntity
from modules.shared import EntityIdVO


class ObjectRepositoryProtocol(Protocol):
    def get_by_id(self, object_id: EntityIdVO) -> ObjectEntity | None: ...

    def get_by_tenant_and_plural_name(
        self,
        tenant_id: EntityIdVO,
        plural_name: str,
    ) -> ObjectEntity | None: ...

    def save(self, object_entity: ObjectEntity) -> None: ...

    def delete(self, object_id: EntityIdVO) -> None: ...
