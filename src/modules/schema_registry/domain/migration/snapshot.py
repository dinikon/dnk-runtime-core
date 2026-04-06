from __future__ import annotations

from dataclasses import dataclass

from src.modules.schema_registry.domain.field.enum.sql_type_preset import (
    SqlTypePresetEnum,
)


@dataclass(frozen=True, slots=True)
class ColumnSnapshot:
    name: str
    sql_preset: SqlTypePresetEnum
    is_nullable: bool
    default_value: str | None


@dataclass(frozen=True, slots=True)
class IndexSnapshot:
    name: str
    columns: tuple[str, ...]
    is_unique: bool


@dataclass(frozen=True, slots=True)
class ForeignKeySnapshot:
    name: str
    source_columns: tuple[str, ...]
    target_table_name: str
    target_columns: tuple[str, ...]
    on_delete: str


@dataclass(frozen=True, slots=True)
class TableSnapshot:
    name: str
    columns: tuple[ColumnSnapshot, ...]
    indexes: tuple[IndexSnapshot, ...] = ()
    foreign_keys: tuple[ForeignKeySnapshot, ...] = ()

    def get_column(self, name: str) -> ColumnSnapshot | None:
        normalized = name.strip()
        for item in self.columns:
            if item.name == normalized:
                return item
        return None

    def get_index(self, name: str) -> IndexSnapshot | None:
        normalized = name.strip()
        for item in self.indexes:
            if item.name == normalized:
                return item
        return None

    def get_foreign_key(self, name: str) -> ForeignKeySnapshot | None:
        normalized = name.strip()
        for item in self.foreign_keys:
            if item.name == normalized:
                return item
        return None


@dataclass(frozen=True, slots=True)
class PhysicalSchemaSnapshot:
    schema_name: str
    tables: tuple[TableSnapshot, ...]

    def get_table(self, name: str) -> TableSnapshot | None:
        normalized = name.strip()
        for item in self.tables:
            if item.name == normalized:
                return item
        return None
