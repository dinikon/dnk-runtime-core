from __future__ import annotations

from src.modules.runtime_schema.application.dto import ListObjectFieldDefinitionsResultDTO
from src.modules.runtime_schema.application.mappers import field_metadata_to_dto
from src.modules.runtime_schema.application.queries import (
    ListObjectFieldDefinitionsQuery,
)
from src.modules.runtime_schema.domain.errors import ObjectMetadataNotFoundError
from src.modules.runtime_schema.domain.repositories import (
    FieldMetadataRepositoryProtocol,
    ObjectMetadataRepositoryProtocol,
)


class ListObjectFieldDefinitionsUseCase:
    def __init__(
        self,
        *,
        object_metadata_repository: ObjectMetadataRepositoryProtocol,
        field_metadata_repository: FieldMetadataRepositoryProtocol,
    ):
        self._object_metadata_repository = object_metadata_repository
        self._field_metadata_repository = field_metadata_repository

    async def execute(
        self,
        query: ListObjectFieldDefinitionsQuery,
    ) -> ListObjectFieldDefinitionsResultDTO:
        object_metadata = await self._object_metadata_repository.get_by_id(
            query.object_metadata_id
        )
        if object_metadata is None:
            raise ObjectMetadataNotFoundError(str(query.object_metadata_id))

        fields = await self._field_metadata_repository.list_by_object_metadata_id(
            query.object_metadata_id
        )

        return ListObjectFieldDefinitionsResultDTO(
            object_metadata_id=query.object_metadata_id,
            fields=tuple(field_metadata_to_dto(item) for item in fields),
        )


__all__ = ["ListObjectFieldDefinitionsUseCase"]
