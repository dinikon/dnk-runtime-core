from __future__ import annotations

from src.modules.runtime_schema.application.relations.dto import (
    DeleteRelationCommandDTO,
    DeleteRelationResultDTO,
)
from src.modules.runtime_schema.application.relations.ports.repositories import (
    RelationMetadataRepositoryProtocol,
    RuntimeSchemaFieldRepositoryProtocol,
    RuntimeSchemaObjectRepositoryProtocol,
)
from src.modules.runtime_schema.application.relations.ports.schema_manager import (
    RelationSchemaManagerProtocol,
)
from src.modules.runtime_schema.domain.errors import RelationMetadataNotFoundError


class DeleteRelationUseCase:
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
        dto: DeleteRelationCommandDTO,
    ) -> DeleteRelationResultDTO:
        relation = await self._relations_repository.get_by_id(dto.relation_id)
        if relation is None:
            raise RelationMetadataNotFoundError(dto.relation_id)

        source_object = await self._objects_repository.get_by_id(
            relation.source_object_metadata_id
        )
        target_object = await self._objects_repository.get_by_id(
            relation.target_object_metadata_id
        )
        source_field = None
        target_field = None
        if relation.source_field_metadata_id is not None:
            source_field = await self._fields_repository.get_by_id(
                relation.source_field_metadata_id
            )
        if relation.target_field_metadata_id is not None:
            target_field = await self._fields_repository.get_by_id(
                relation.target_field_metadata_id
            )
        if source_object is None or target_object is None:
            raise RelationMetadataNotFoundError(dto.relation_id)

        await self._schema_manager.drop_relation(
            schema=dto.schema,
            relation=relation,
            source_object=source_object,
            source_field=source_field,
            target_object=target_object,
            target_field=target_field,
        )
        if source_field is not None and relation.is_owner_relation:
            source_field.unbind_relation()
            await self._fields_repository.save(source_field)

        relation.deactivate()
        await self._relations_repository.save(relation)
        return DeleteRelationResultDTO(ok=True)
