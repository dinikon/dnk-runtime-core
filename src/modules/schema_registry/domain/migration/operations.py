from dataclasses import dataclass
from typing import Literal


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
    column_type: str
    is_nullable: bool
    default: str | None = None


@dataclass(frozen=True, slots=True)
class DropColumnOperation:
    schema_name: str
    table_name: str
    column_name: str


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


MigrationOperation = (
    CreateSchemaOperation
    | CreateTableOperation
    | DropTableOperation
    | AddColumnOperation
    | DropColumnOperation
    | CreateIndexOperation
    | DropIndexOperation
    | AddForeignKeyOperation
)
