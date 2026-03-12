from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True, frozen=True)
class SyncTenantSystemSchemaCommandDTO:
    tenant_id: UUID
    data_source_id: UUID
    schema: str


@dataclass(slots=True, frozen=True)
class SyncTenantSystemSchemaResultDTO:
    version: str
    manifest_hash: str
    applied_operations: int
    created_tables: int
    added_columns: int
    created_indexes: int
    dropped_tables: int = 0
    dropped_columns: int = 0

