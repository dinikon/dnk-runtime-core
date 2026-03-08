from __future__ import annotations

import uuid6

from src.modules.runtime_schema.application.relations.dto import (
    CreateRelationCommandDTO,
    CreateRelationResultDTO,
)
from src.modules.runtime_schema.application.relations.ports.repositories import (
    RelationMetadataRepositoryProtocol,
    RuntimeSchemaFieldRepositoryProtocol,
    RuntimeSchemaObjectRepositoryProtocol,
)
from src.modules.runtime_schema.application.relations.ports.schema_manager import (
    RelationSchemaManagerProtocol,
)
from src.modules.runtime_schema.domain.entities import RelationMetadata
from src.modules.runtime_schema.domain.errors import (
    CrossTenantRelationError,
    FieldMetadataNotFoundError,
    FieldMetadataObjectMismatchError,
    InvalidRelationFieldTypeError,
    ObjectMetadataNotFoundError,
    RelationFieldAlreadyBoundError,
    RelationJunctionTableAlreadyExistsError,
    RelationOwnerFieldRequiredError,
)
from src.modules.runtime_schema.domain.value_objects import (
    RuntimeSchemaFieldType,
    RuntimeSchemaRelationKind,
    RuntimeSchemaRelationOnDelete,
)


class CreateRelationUseCase:
    def __init__(
        self,
        objects_repository: RuntimeSchemaObjectRepositoryProtocol,
        fields_repository: RuntimeSchemaFieldRepositoryProtocol,
        relations_repository: RelationMetadataRepositoryProtocol,
        schema_manager: RelationSchemaManagerProtocol,
    ):
        self._objects_repository = objects_repository
        self._fields_repository = fields_repository
        self._relations_repository = relations_repository
        self._schema_manager = schema_manager

    async def execute(
        self,
        dto: CreateRelationCommandDTO,
    ) -> CreateRelationResultDTO:
        relation_kind = RuntimeSchemaRelationKind(dto.kind)
        if relation_kind == RuntimeSchemaRelationKind.ONE_TO_MANY:
            relation_kind = RuntimeSchemaRelationKind.MANY_TO_ONE

        source_object = await self._objects_repository.get_by_id(
            dto.source_object_metadata_id
        )
        target_object = await self._objects_repository.get_by_id(
            dto.target_object_metadata_id
        )
        if source_object is None:
            raise ObjectMetadataNotFoundError(dto.source_object_metadata_id)
        if target_object is None:
            raise ObjectMetadataNotFoundError(dto.target_object_metadata_id)
        if (
            source_object.tenant_id != dto.tenant_id
            or target_object.tenant_id != dto.tenant_id
        ):
            raise CrossTenantRelationError()

        target_field = None
        if relation_kind in {
            RuntimeSchemaRelationKind.MANY_TO_ONE,
            RuntimeSchemaRelationKind.ONE_TO_ONE,
        }:
            if dto.target_field_metadata_id is not None:
                target_field = await self._fields_repository.get_by_id(
                    dto.target_field_metadata_id
                )
            else:
                target_field = (
                    await self._fields_repository.get_by_object_and_name_field(
                        target_object.id,
                        "id",
                    )
                )

        source_field = None
        if relation_kind in {
            RuntimeSchemaRelationKind.MANY_TO_ONE,
            RuntimeSchemaRelationKind.ONE_TO_ONE,
        }:
            if dto.source_field_metadata_id is None:
                raise RelationOwnerFieldRequiredError()
            source_field = await self._fields_repository.get_by_id(
                dto.source_field_metadata_id
            )
            if source_field is None:
                raise FieldMetadataNotFoundError(dto.source_field_metadata_id)
            if target_field is None:
                target_field_reference = (
                    dto.target_field_metadata_id
                    if dto.target_field_metadata_id is not None
                    else f"{target_object.id}:id"
                )
                raise FieldMetadataNotFoundError(target_field_reference)
            if (
                source_field.tenant_id != dto.tenant_id
                or target_field.tenant_id != dto.tenant_id
            ):
                raise CrossTenantRelationError()
            if source_field.object_metadata_id != source_object.id:
                raise FieldMetadataObjectMismatchError(
                    source_field.id, source_object.id
                )
            if target_field.object_metadata_id != target_object.id:
                raise FieldMetadataObjectMismatchError(
                    target_field.id, target_object.id
                )
            if source_field.field_type != RuntimeSchemaFieldType.UUID:
                raise InvalidRelationFieldTypeError(
                    source_field.name_field,
                    source_field.field_type.value,
                )
            if target_field.field_type != RuntimeSchemaFieldType.UUID:
                raise InvalidRelationFieldTypeError(
                    target_field.name_field,
                    target_field.field_type.value,
                )
            existing_relation = await self._relations_repository.get_by_source_field_id(
                source_field.id
            )
            if existing_relation is not None and existing_relation.is_active:
                raise RelationFieldAlreadyBoundError(source_field.id)

        if relation_kind == RuntimeSchemaRelationKind.MANY_TO_ONE:
            relation = RelationMetadata.create_many_to_one(
                tenant_id=dto.tenant_id,
                source_object_metadata_id=source_object.id,
                source_field_metadata_id=source_field.id,
                target_object_metadata_id=target_object.id,
                target_field_metadata_id=target_field.id,
                reverse_name_field=dto.reverse_name_field,
                reverse_label=dto.reverse_label,
                on_delete=RuntimeSchemaRelationOnDelete(dto.on_delete),
                is_required=dto.is_required,
                is_system=dto.is_system,
            )
            source_field.bind_relation(target_object.id, target_field.id)
            await self._fields_repository.save(source_field)
        elif relation_kind == RuntimeSchemaRelationKind.ONE_TO_ONE:
            relation = RelationMetadata.create_one_to_one(
                tenant_id=dto.tenant_id,
                source_object_metadata_id=source_object.id,
                source_field_metadata_id=source_field.id,
                target_object_metadata_id=target_object.id,
                target_field_metadata_id=target_field.id,
                reverse_name_field=dto.reverse_name_field,
                reverse_label=dto.reverse_label,
                on_delete=RuntimeSchemaRelationOnDelete(dto.on_delete),
                is_required=dto.is_required,
                is_system=dto.is_system,
            )
            source_field.bind_relation(target_object.id, target_field.id)
            await self._fields_repository.save(source_field)
        else:
            junction_table_name = dto.junction_table_name
            if not junction_table_name:
                relation_suffix = uuid6.uuid7().hex[:8]
                junction_table_name = (
                    f"rel_{source_object.name_singular}_"
                    f"{target_object.name_singular}_{relation_suffix}"
                )
            if await self._relations_repository.exists_by_junction_table_name(
                junction_table_name
            ):
                raise RelationJunctionTableAlreadyExistsError(junction_table_name)
            relation = RelationMetadata.create_many_to_many(
                tenant_id=dto.tenant_id,
                source_object_metadata_id=source_object.id,
                target_object_metadata_id=target_object.id,
                junction_table_name=junction_table_name,
                reverse_name_field=dto.reverse_name_field,
                reverse_label=dto.reverse_label,
                is_system=dto.is_system,
            )
            source_field = None
            target_field = None

        await self._relations_repository.add(relation)
        await self._schema_manager.ensure_relation(
            schema=dto.schema,
            relation=relation,
            source_object=source_object,
            source_field=source_field,
            target_object=target_object,
            target_field=target_field,
        )
        return CreateRelationResultDTO(
            relation_id=relation.id,
            kind=relation.kind.value,
            reverse_kind=relation.reverse_kind.value,
            junction_table_name=relation.junction_table_name,
        )
