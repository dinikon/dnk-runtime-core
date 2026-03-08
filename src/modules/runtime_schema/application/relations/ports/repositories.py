from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.modules.runtime_schema.domain.entities import (
    FieldMetadata,
    ObjectMetadata,
    RelationMetadata,
)


class RuntimeSchemaObjectRepositoryProtocol(Protocol):
    async def get_by_id(self, object_metadata_id: UUID) -> ObjectMetadata | None: ...
    async def get_by_tenant_and_name_singular(
        self,
        tenant_id: UUID,
        name_singular: str,
    ) -> ObjectMetadata | None: ...


class RuntimeSchemaFieldRepositoryProtocol(Protocol):
    async def get_by_id(self, field_metadata_id: UUID) -> FieldMetadata | None: ...
    async def save(self, field_metadata: FieldMetadata) -> None: ...
    async def get_by_object_and_name_field(
        self,
        object_metadata_id: UUID,
        name_field: str,
    ) -> FieldMetadata | None: ...


class RelationMetadataRepositoryProtocol(Protocol):
    async def add(self, relation_metadata: RelationMetadata) -> None: ...
    async def save(self, relation_metadata: RelationMetadata) -> None: ...
    async def get_by_id(self, relation_id: UUID) -> RelationMetadata | None: ...
    async def get_by_source_field_id(
        self,
        source_field_metadata_id: UUID,
    ) -> RelationMetadata | None: ...
    async def exists_by_junction_table_name(
        self,
        junction_table_name: str,
    ) -> bool: ...
