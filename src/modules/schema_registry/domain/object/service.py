from __future__ import annotations

from collections.abc import Callable

from src.modules.shared import ClockPort, EntityIdVO
from src.modules.schema_registry.domain.field.service import FieldTypeService
from src.modules.schema_registry.domain.object.entity import ObjectEntity
from src.modules.schema_registry.domain.object.repository import (
    ObjectRepositoryProtocol,
)
from src.modules.schema_registry.domain.object.value_object.object_label import (
    ObjectLabelVO,
)
from src.modules.schema_registry.domain.object.value_object.object_name import (
    ObjectNameVO,
)
from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed


class ObjectService:
    def __init__(
        self,
        object_repository: ObjectRepositoryProtocol,
        clock: ClockPort,
        id_provider: Callable[[], EntityIdVO],
        field_type_service: FieldTypeService,
    ) -> None:
        self._object_repository = object_repository
        self._clock = clock
        self._id_provider = id_provider
        self._field_type_service = field_type_service

    async def replace_all_for_tenant_from_seed(
        self,
        *,
        tenant_id: EntityIdVO,
        data_source_id: EntityIdVO,
        seed: SchemaSeed,
    ) -> list[ObjectEntity]:
        now = self._clock.now()
        objects: list[ObjectEntity] = []

        for object_seed in seed.objects:
            object_entity = ObjectEntity.create(
                id_=self._id_provider(),
                tenant_id=tenant_id,
                data_source_id=data_source_id,
                now=now,
                object_name=ObjectNameVO(
                    singular=object_seed.singular_name,
                    plural=object_seed.plural_name,
                ),
                object_label=ObjectLabelVO(
                    singular=object_seed.singular_label,
                    plural=object_seed.plural_label,
                ),
                description=object_seed.description,
            )
            object_entity.add_fields_from_seed(
                now=now,
                seeds=object_seed.fields,
                field_id_provider=self._id_provider,
                field_type_mapper=self._field_type_service.from_seed_type,
            )
            objects.append(object_entity)

        await self._object_repository.replace_all_for_tenant(
            tenant_id=tenant_id,
            objects=objects,
        )
        return objects

    async def list_by_tenant_id(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> list[ObjectEntity]:
        return await self._object_repository.list_by_tenant_id(tenant_id=tenant_id)
