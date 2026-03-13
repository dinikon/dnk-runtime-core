from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from src.modules.runtime_schema.domain.field.entity import FieldMetadataEntity
from src.modules.runtime_schema.domain.object.entity import ObjectMetadataEntity


@dataclass(frozen=True, slots=True)
class SystemFieldDefinition:
    name: str
    field_type: str
    label: str
    description: str | None = None
    icon: str | None = None
    is_unique: bool = False
    is_index: bool = False
    is_nullable: bool = True
    is_ui_read_only: bool = False
    is_searchable: bool = False
    options: dict[str, object] | None = None
    settings: dict[str, object] | None = None
    default_value: dict[str, object] | None = None
    relation_target_object: str | None = None
    relation_target_field: str | None = None


@dataclass(frozen=True, slots=True)
class SystemObjectDefinition:
    key: str
    name_singular: str
    name_plural: str
    label_singular: str
    label_plural: str
    description: str | None = None
    icon: str | None = None
    shortcut: str | None = None
    duplicate_criteria: dict[str, object] | None = None
    fields: tuple[SystemFieldDefinition, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class LoadedSystemManifest:
    version: str
    manifest_hash: str
    module: str | None
    objects: tuple[SystemObjectDefinition, ...]


@dataclass(frozen=True, slots=True)
class MetadataBundle:
    version: str
    manifest_hash: str
    objects_by_key: dict[str, ObjectMetadataEntity]
    fields_by_object_key: dict[str, tuple[FieldMetadataEntity, ...]]

    @property
    def objects(self) -> tuple[ObjectMetadataEntity, ...]:
        return tuple(self.objects_by_key.values())

    @property
    def fields(self) -> tuple[FieldMetadataEntity, ...]:
        values: list[FieldMetadataEntity] = []
        for object_fields in self.fields_by_object_key.values():
            values.extend(object_fields)
        return tuple(values)


@dataclass(frozen=True, slots=True)
class ColumnSpec:
    name: str
    sql_type: str
    nullable: bool = True
    is_primary_key: bool = False
    default_sql: str | None = None
    references_table: str | None = None
    references_column: str | None = None
    on_delete: str | None = None


@dataclass(frozen=True, slots=True)
class IndexSpec:
    name: str
    columns: tuple[str, ...]
    unique: bool = False


@dataclass(frozen=True, slots=True)
class TableSpec:
    name: str
    columns: tuple[ColumnSpec, ...]
    indexes: tuple[IndexSpec, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SchemaSnapshot:
    tables: dict[str, TableSpec]

    @classmethod
    def empty(cls) -> SchemaSnapshot:
        return cls(tables={})


@dataclass(frozen=True, slots=True)
class TableToCreate:
    table: TableSpec


@dataclass(frozen=True, slots=True)
class ColumnToAdd:
    table_name: str
    column: ColumnSpec


@dataclass(frozen=True, slots=True)
class IndexToCreate:
    table_name: str
    index: IndexSpec


@dataclass(frozen=True, slots=True)
class TableToDrop:
    table_name: str


@dataclass(frozen=True, slots=True)
class ColumnToDrop:
    table_name: str
    column_name: str


@dataclass(frozen=True, slots=True)
class DdlDiff:
    tables_to_create: tuple[TableToCreate, ...] = field(default_factory=tuple)
    columns_to_add: tuple[ColumnToAdd, ...] = field(default_factory=tuple)
    indexes_to_create: tuple[IndexToCreate, ...] = field(default_factory=tuple)
    tables_to_drop: tuple[TableToDrop, ...] = field(default_factory=tuple)
    columns_to_drop: tuple[ColumnToDrop, ...] = field(default_factory=tuple)

    def is_empty(self) -> bool:
        return not (
            self.tables_to_create
            or self.columns_to_add
            or self.indexes_to_create
            or self.tables_to_drop
            or self.columns_to_drop
        )


class DdlOperationKind(StrEnum):
    CREATE_TABLE = "create_table"
    ADD_COLUMN = "add_column"
    CREATE_INDEX = "create_index"
    DROP_COLUMN = "drop_column"
    DROP_TABLE = "drop_table"
    RENAME_TABLE = "rename_table"


@dataclass(frozen=True, slots=True)
class DdlOperation:
    key: str
    kind: DdlOperationKind
    sql: str


@dataclass(frozen=True, slots=True)
class DdlPlan:
    operations: tuple[DdlOperation, ...] = field(default_factory=tuple)

    def is_empty(self) -> bool:
        return len(self.operations) == 0


@dataclass(frozen=True, slots=True)
class MigrationJournalEntry:
    operation_key: str
    operation_sql: str
    status: str
    error_message: str | None
    created_at: datetime
    applied_at: datetime | None

    @classmethod
    def applied(cls, *, operation_key: str, operation_sql: str) -> MigrationJournalEntry:
        now = datetime.now(UTC)
        return cls(
            operation_key=operation_key,
            operation_sql=operation_sql,
            status="APPLIED",
            error_message=None,
            created_at=now,
            applied_at=now,
        )

    @classmethod
    def failed(
        cls,
        *,
        operation_key: str,
        operation_sql: str,
        error_message: str,
    ) -> MigrationJournalEntry:
        now = datetime.now(UTC)
        return cls(
            operation_key=operation_key,
            operation_sql=operation_sql,
            status="FAILED",
            error_message=error_message,
            created_at=now,
            applied_at=None,
        )


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    operations: tuple[DdlOperation, ...]
    journal_entries: tuple[MigrationJournalEntry, ...]

    @property
    def applied_operations(self) -> int:
        return len(self.operations)
