from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.modules.runtime_schema.domain.entities import FieldMetadata, ObjectMetadata


class ObjectMetadataRepositoryProtocol(Protocol):
    async def add(self, object_metadata: ObjectMetadata) -> None: ...
    async def save(self, object_metadata: ObjectMetadata) -> None: ...
    async def get_by_tenant_and_name_singular(
        self,
        tenant_id: UUID,
        name_singular: str,
    ) -> ObjectMetadata | None: ...


class FieldMetadataRepositoryProtocol(Protocol):
    async def add(self, field_metadata: FieldMetadata) -> None: ...
    async def save(self, field_metadata: FieldMetadata) -> None: ...
    async def get_by_object_and_name_field(
        self,
        object_metadata_id: UUID,
        name_field: str,
    ) -> FieldMetadata | None: ...
