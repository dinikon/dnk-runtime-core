from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from src.modules.runtime_schema.domain.field.entity import FieldMetadataEntity
from src.modules.runtime_schema.domain.field.value_object import FieldIdVO
from src.modules.runtime_schema.domain.object.entity import ObjectMetadataEntity
from src.modules.runtime_schema.domain.object.value_object import ObjectIdVO
from src.modules.runtime_schema.domain.source.value_object import DataSourceIdVO
from src.modules.runtime_schema.infrastructure.ddl_models import (
    DdlDiff,
    DdlPlan,
    ExecutionReport,
    LoadedSystemManifest,
    MetadataBundle,
    MigrationJournalEntry,
    SchemaSnapshot,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class SchemaVersionEntry:
    tenant_id: EntityIdVO
    data_source_id: DataSourceIdVO
    schema: str
    version: str
    manifest_hash: str
    updated_at: datetime


class SystemModelRegistryReaderProtocol(Protocol):
    async def load_system_manifest(self) -> LoadedSystemManifest: ...


class MetadataCompilerProtocol(Protocol):
    def compile_system_schema(
        self,
        *,
        manifest: LoadedSystemManifest,
        tenant_id: EntityIdVO,
        data_source_id: DataSourceIdVO,
    ) -> MetadataBundle: ...


class FieldLayoutCompilerProtocol(Protocol):
    def compile_layout(self, *, objects: list[ObjectMetadataEntity], fields: list[FieldMetadataEntity]) -> SchemaSnapshot: ...


class SchemaIntrospectorProtocol(Protocol):
    async def introspect(self, *, schema: str) -> SchemaSnapshot: ...


class DdlDiffEngineProtocol(Protocol):
    def diff(
        self,
        *,
        expected: SchemaSnapshot,
        actual: SchemaSnapshot,
        allow_destructive: bool = False,
    ) -> DdlDiff: ...


class DdlPlanBuilderProtocol(Protocol):
    def build(self, *, schema: str, diff: DdlDiff) -> DdlPlan: ...


class DdlExecutorProtocol(Protocol):
    async def execute(
        self,
        *,
        tenant_id: EntityIdVO,
        data_source_id: DataSourceIdVO,
        schema: str,
        plan: DdlPlan,
    ) -> ExecutionReport: ...


class SchemaVersionRepositoryProtocol(Protocol):
    async def get(
        self,
        *,
        tenant_id: EntityIdVO,
        schema: str,
    ) -> SchemaVersionEntry | None: ...

    async def upsert(self, entry: SchemaVersionEntry) -> None: ...


class SchemaMigrationJournalRepositoryProtocol(Protocol):
    async def add_entries(
        self,
        *,
        tenant_id: EntityIdVO,
        data_source_id: DataSourceIdVO,
        schema: str,
        entries: list[MigrationJournalEntry],
    ) -> None: ...


class SchemaLockServiceProtocol(Protocol):
    def lock(
        self,
        *,
        tenant_id: EntityIdVO,
        schema: str,
    ) -> AbstractAsyncContextManager[None]: ...


class ObjectMetadataRepositoryProtocol(Protocol):
    async def add(self, entity: ObjectMetadataEntity) -> None: ...
    async def save(self, entity: ObjectMetadataEntity) -> None: ...
    async def delete(self, *, object_id: ObjectIdVO) -> None: ...
    async def get_by_id(self, *, object_id: ObjectIdVO) -> ObjectMetadataEntity | None: ...
    async def get_by_name(
        self,
        *,
        tenant_id: EntityIdVO,
        data_source_id: DataSourceIdVO,
        object_name_singular: str,
    ) -> ObjectMetadataEntity | None: ...

    async def list_by_tenant_data_source(
        self,
        *,
        tenant_id: EntityIdVO,
        data_source_id: DataSourceIdVO,
    ) -> list[ObjectMetadataEntity]: ...


class FieldMetadataRepositoryProtocol(Protocol):
    async def add(self, entity: FieldMetadataEntity) -> None: ...
    async def save(self, entity: FieldMetadataEntity) -> None: ...
    async def delete(self, *, field_id: FieldIdVO) -> None: ...
    async def get_by_id(self, *, field_id: FieldIdVO) -> FieldMetadataEntity | None: ...

    async def get_by_object_and_name(
        self,
        *,
        object_id: ObjectIdVO,
        field_name: str,
    ) -> FieldMetadataEntity | None: ...

    async def list_by_object(
        self,
        *,
        object_id: ObjectIdVO,
    ) -> list[FieldMetadataEntity]: ...

    async def list_by_tenant(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> list[FieldMetadataEntity]: ...

