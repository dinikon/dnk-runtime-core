from __future__ import annotations

from typing import Protocol

from src.modules.schema_registry.domain.datasource.service import DataSourceService
from src.modules.schema_registry.domain.error import (
    RuntimeObjectDescriptorError,
    RuntimeObjectNotFoundError,
    SchemaRegistryMetadataInconsistentError,
)
from src.modules.schema_registry.domain.object.service import ObjectService
from src.modules.schema_registry.runtime.descriptor import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)
from src.modules.shared import EntityIdVO


class RuntimeObjectResolverProtocol(Protocol):
    """Порт преобразования schema_registry metadata в runtime descriptor."""

    async def resolve(
        self,
        tenant_id: EntityIdVO,
        object_name: str,
    ) -> RuntimeObjectDescriptor:
        """Возвращает descriptor runtime-объекта tenant по имени."""
        ...


class SchemaRegistryRuntimeObjectResolver:
    """Resolver, который строит runtime descriptor из schema_registry metadata."""

    def __init__(
        self,
        data_source_service: DataSourceService,
        object_service: ObjectService,
    ) -> None:
        """Инициализирует resolver сервисами datasource и object metadata."""
        self._data_source_service = data_source_service
        self._object_service = object_service

    async def resolve(
        self,
        tenant_id: EntityIdVO,
        object_name: str,
    ) -> RuntimeObjectDescriptor:
        """Собирает descriptor объекта и проверяет consistency metadata.

        Resolver связывает datasource tenant с object metadata, переносит поля в
        immutable runtime descriptors и гарантирует наличие primary key поля `id`.
        """
        normalized_object_name = object_name.strip()
        datasource = await self._data_source_service.get_required_by_tenant(
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
        if object_entity.data_source_id != datasource.id:
            raise SchemaRegistryMetadataInconsistentError(
                "schema_registry object metadata has mismatched data_source_id."
            )

        fields = tuple(
            RuntimeFieldDescriptor(
                name=field.field_name.value,
                type_code=field.field_type.code.value,
                is_nullable=field.is_nullable,
                default_value=field.default_value,
                options=dict(field.options),
                settings=dict(field.settings),
                kind=field.kind.value,
            )
            for field in object_entity.fields
        )

        field_names = {field.name for field in fields}
        if "id" not in field_names:
            raise RuntimeObjectDescriptorError(
                "Runtime object descriptor requires an 'id' field."
            )

        return RuntimeObjectDescriptor(
            schema_name=datasource.schema_name.value,
            object_name=object_entity.object_name.singular,
            table_name=object_entity.object_name.plural,
            pk="id",
            title_field="id",
            fields=fields,
            relations=(),
            kind=object_entity.kind.value,
        )
