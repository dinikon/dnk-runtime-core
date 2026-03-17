from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.modules.runtime_schema.domain.entities import (
    DataSource,
    FieldMetadata,
    ObjectMetadata,
)


class DataSourceRepositoryProtocol(Protocol):
    async def add(self, data_source: DataSource) -> None: ...
    async def get_by_id(self, data_source_id: UUID) -> DataSource | None: ...
    async def list_by_tenant_id(self, tenant_id: UUID) -> tuple[DataSource, ...]: ...
    async def delete_by_id(self, data_source_id: UUID) -> bool: ...


class ObjectMetadataRepositoryProtocol(Protocol):
    async def add(self, object_metadata: ObjectMetadata) -> None: ...
    async def get_by_id(self, object_metadata_id: UUID) -> ObjectMetadata | None: ...
    async def get_by_name(
        self,
        *,
        tenant_id: UUID,
        name_singular: str,
    ) -> ObjectMetadata | None: ...
    async def list_by_tenant_id(
        self,
        tenant_id: UUID,
    ) -> tuple[ObjectMetadata, ...]: ...


class FieldMetadataRepositoryProtocol(Protocol):
    async def add(self, field_metadata: FieldMetadata) -> None: ...
    async def deactivate(self, field_metadata: FieldMetadata) -> None: ...
    async def get_by_id(self, field_metadata_id: UUID) -> FieldMetadata | None: ...
    async def get_by_name(
        self,
        *,
        object_metadata_id: UUID,
        name: str,
    ) -> FieldMetadata | None: ...
    async def list_by_object_metadata_id(
        self,
        object_metadata_id: UUID,
    ) -> tuple[FieldMetadata, ...]: ...
    async def delete_by_id(self, field_metadata_id: UUID) -> bool: ...


__all__ = [
    "DataSourceRepositoryProtocol",
    "FieldMetadataRepositoryProtocol",
    "ObjectMetadataRepositoryProtocol",
]
