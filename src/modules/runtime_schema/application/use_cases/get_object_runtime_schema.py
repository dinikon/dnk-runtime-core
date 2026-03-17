from __future__ import annotations

from src.modules.runtime_schema.application.dto import ObjectRuntimeSchemaDTO
from src.modules.runtime_schema.application.mappers import (
    field_metadata_to_dto,
    object_metadata_to_dto,
)
from src.modules.runtime_schema.application.queries import GetObjectRuntimeSchemaQuery
from src.modules.runtime_schema.domain.errors import ObjectMetadataNotFoundError
from src.modules.runtime_schema.domain.repositories import (
    FieldMetadataRepositoryProtocol,
    ObjectMetadataRepositoryProtocol,
)


class GetObjectRuntimeSchemaUseCase:
    def __init__(
        self,
        *,
        object_metadata_repository: ObjectMetadataRepositoryProtocol,
        field_metadata_repository: FieldMetadataRepositoryProtocol,
    ):
        self._object_metadata_repository = object_metadata_repository
        self._field_metadata_repository = field_metadata_repository

    async def execute(self, query: GetObjectRuntimeSchemaQuery) -> ObjectRuntimeSchemaDTO:
        object_metadata = await self._object_metadata_repository.get_by_name(
            tenant_id=query.tenant_id,
            name_singular=query.name_singular.strip(),
        )
        if object_metadata is None:
            raise ObjectMetadataNotFoundError(query.name_singular)

        fields = await self._field_metadata_repository.list_by_object_metadata_id(
            object_metadata.id
        )

        return ObjectRuntimeSchemaDTO(
            object_metadata=object_metadata_to_dto(object_metadata),
            fields=tuple(field_metadata_to_dto(item) for item in fields),
        )


__all__ = ["GetObjectRuntimeSchemaUseCase"]
