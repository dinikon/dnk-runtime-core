from dataclasses import dataclass
from typing import TypeAlias

from src.modules.schema_registry.application.migration.sql_type_preset import (
    SqlTypePresetEnum,
)


@dataclass(frozen=True, slots=True)
class CreateSchemaOperation:
    schema_name: str


@dataclass(frozen=True, slots=True)
class CreateTableOperation:
    schema_name: str
    table_name: str


@dataclass(frozen=True, slots=True)
class DropTableOperation:
    schema_name: str
    table_name: str


@dataclass(frozen=True, slots=True)
class AddColumnOperation:
    schema_name: str
    table_name: str
    column_name: str
    sql_preset: SqlTypePresetEnum
    is_nullable: bool
    default_value: str | None = None


@dataclass(frozen=True, slots=True)
class DropColumnOperation:
    schema_name: str
    table_name: str
    column_name: str


@dataclass(frozen=True, slots=True)
class AlterColumnDefaultOperation:
    schema_name: str
    table_name: str
    column_name: str
    default_value: str | None


@dataclass(frozen=True, slots=True)
class AlterColumnNullableOperation:
    schema_name: str
    table_name: str
    column_name: str
    is_nullable: bool


@dataclass(frozen=True, slots=True)
class CreateIndexOperation:
    schema_name: str
    table_name: str
    index_name: str
    columns: tuple[str, ...]
    is_unique: bool


@dataclass(frozen=True, slots=True)
class DropIndexOperation:
    schema_name: str
    index_name: str


@dataclass(frozen=True, slots=True)
class AddForeignKeyOperation:
    schema_name: str
    table_name: str
    constraint_name: str
    column_name: str
    target_schema_name: str
    target_table_name: str
    target_column_name: str
    on_delete: str


@dataclass(frozen=True, slots=True)
class DropForeignKeyOperation:
    schema_name: str
    table_name: str
    constraint_name: str


MigrationOperation: TypeAlias = (
    CreateSchemaOperation
    | CreateTableOperation
    | DropTableOperation
    | AddColumnOperation
    | DropColumnOperation
    | AlterColumnDefaultOperation
    | AlterColumnNullableOperation
    | CreateIndexOperation
    | DropIndexOperation
    | AddForeignKeyOperation
    | DropForeignKeyOperation
)
