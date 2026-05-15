from dataclasses import dataclass
from typing import TypeAlias

from src.modules.schema_registry.application.migration.sql_type_preset import (
    SqlTypePresetEnum,
)


@dataclass(frozen=True, slots=True)
class CreateSchemaOperation:
    """Операция создания PostgreSQL-схемы tenant."""

    schema_name: str


@dataclass(frozen=True, slots=True)
class CreateTableOperation:
    """Операция создания таблицы в tenant-схеме."""

    schema_name: str
    table_name: str


@dataclass(frozen=True, slots=True)
class DropTableOperation:
    """Destructive-операция удаления таблицы из tenant-схемы."""

    schema_name: str
    table_name: str


@dataclass(frozen=True, slots=True)
class AddColumnOperation:
    """Операция добавления колонки с каноническим SQL-типом и default."""

    schema_name: str
    table_name: str
    column_name: str
    sql_preset: SqlTypePresetEnum
    is_nullable: bool
    default_value: str | None = None


@dataclass(frozen=True, slots=True)
class DropColumnOperation:
    """Destructive-операция удаления колонки из таблицы tenant."""

    schema_name: str
    table_name: str
    column_name: str


@dataclass(frozen=True, slots=True)
class AlterColumnDefaultOperation:
    """Операция изменения или удаления default-значения колонки."""

    schema_name: str
    table_name: str
    column_name: str
    default_value: str | None


@dataclass(frozen=True, slots=True)
class AlterColumnNullableOperation:
    """Операция изменения nullable-флага колонки."""

    schema_name: str
    table_name: str
    column_name: str
    is_nullable: bool


@dataclass(frozen=True, slots=True)
class AddPrimaryKeyOperation:
    """Операция добавления primary key constraint к таблице."""

    schema_name: str
    table_name: str
    constraint_name: str
    columns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DropPrimaryKeyOperation:
    """Destructive-операция удаления primary key constraint."""

    schema_name: str
    table_name: str
    constraint_name: str


@dataclass(frozen=True, slots=True)
class CreateIndexOperation:
    """Операция создания обычного или unique-индекса."""

    schema_name: str
    table_name: str
    index_name: str
    columns: tuple[str, ...]
    is_unique: bool


@dataclass(frozen=True, slots=True)
class DropIndexOperation:
    """Destructive-операция удаления индекса из tenant-схемы."""

    schema_name: str
    index_name: str


@dataclass(frozen=True, slots=True)
class AddForeignKeyOperation:
    """Операция создания foreign key между таблицами tenant-схемы."""

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
    """Destructive-операция удаления foreign key constraint."""

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
    | AddPrimaryKeyOperation
    | DropPrimaryKeyOperation
    | CreateIndexOperation
    | DropIndexOperation
    | AddForeignKeyOperation
    | DropForeignKeyOperation
)
