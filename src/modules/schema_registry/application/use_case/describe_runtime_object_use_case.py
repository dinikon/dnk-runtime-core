from __future__ import annotations

from typing import Protocol

from src.modules.schema_registry.application.dto.runtime_object_description import (
    RuntimeFieldDescriptionDTO,
    RuntimeObjectDescriptionDTO,
)
from src.modules.schema_registry.domain.datasource.service import DataSourceService
from src.modules.schema_registry.domain.error import (
    RuntimeObjectNotFoundError,
    SchemaRegistryMetadataInconsistentError,
)
from src.modules.schema_registry.domain.object.service import ObjectService
from src.modules.shared import EntityIdVO


class DescribeRuntimeObjectUseCaseProtocol(Protocol):
    """Порт use case чтения описания runtime-объекта."""

    async def __call__(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
    ) -> RuntimeObjectDescriptionDTO:
        """Возвращает описание runtime-объекта tenant по singular-имени."""
        ...


class DescribeRuntimeObjectUseCase:
    """Use case чтения runtime metadata объекта через schema_registry."""

    def __init__(
        self,
        data_source_service: DataSourceService,
        object_service: ObjectService,
    ) -> None:
        """Инициализирует use case сервисами datasource и object metadata."""
        self._data_source_service = data_source_service
        self._object_service = object_service

    async def __call__(
        self,
        *,
        tenant_id: EntityIdVO,
        object_name: str,
    ) -> RuntimeObjectDescriptionDTO:
        """Возвращает описание metadata объекта и проверяет его связность."""
        normalized_object_name = object_name.strip()
        data_source = await self._data_source_service.get_required_by_tenant(
            tenant_id=tenant_id,
        )
        object_entity = await self._object_service.get_by_tenant_and_singular_name(
            tenant_id=tenant_id,
            singular_name=normalized_object_name,
        )
        if object_entity is None:
            raise RuntimeObjectNotFoundError(
                tenant_id=str(tenant_id),
                object_name=normalized_object_name,
            )

        if object_entity.tenant_id != tenant_id:
            raise SchemaRegistryMetadataInconsistentError(
                "schema_registry object metadata has mismatched tenant_id."
            )
        if object_entity.data_source_id != data_source.id:
            raise SchemaRegistryMetadataInconsistentError(
                "schema_registry object metadata has mismatched data_source_id."
            )

        return RuntimeObjectDescriptionDTO(
            id=object_entity.id.value,
            singular_label=object_entity.object_label.singular,
            plural_label=object_entity.object_label.plural,
            description=object_entity.description,
            fields=tuple(
                RuntimeFieldDescriptionDTO(
                    id=field.id.value,
                    field_name=field.field_name.value,
                    label=field.label.value,
                    description=field.description,
                    type=field.field_type.code.value,
                    is_nullable=field.is_nullable,
                    default_value=field.default_value,
                    options=dict(field.options),
                )
                for field in object_entity.fields
            ),
        )
