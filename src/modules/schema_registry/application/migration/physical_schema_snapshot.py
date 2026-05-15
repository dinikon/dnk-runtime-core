from __future__ import annotations

from dataclasses import dataclass

from src.modules.schema_registry.application.migration.sql_type_preset import (
    SqlTypePresetEnum,
)


@dataclass(frozen=True, slots=True)
class ColumnSnapshot:
    """Снимок физической колонки PostgreSQL в каноническом виде."""

    name: str
    sql_preset: SqlTypePresetEnum
    is_nullable: bool
    default_value: str | None


@dataclass(frozen=True, slots=True)
class IndexSnapshot:
    """Снимок физического индекса PostgreSQL без primary key индексов."""

    name: str
    columns: tuple[str, ...]
    is_unique: bool


@dataclass(frozen=True, slots=True)
class ForeignKeySnapshot:
    """Снимок foreign key constraint между таблицами."""

    name: str
    source_columns: tuple[str, ...]
    target_table_name: str
    target_columns: tuple[str, ...]
    on_delete: str


@dataclass(frozen=True, slots=True)
class PrimaryKeySnapshot:
    """Снимок primary key constraint таблицы."""

    name: str
    columns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TableSnapshot:
    """Снимок таблицы вместе с колонками, индексами и foreign key."""

    name: str
    columns: tuple[ColumnSnapshot, ...]
    primary_key: PrimaryKeySnapshot | None = None
    indexes: tuple[IndexSnapshot, ...] = ()
    foreign_keys: tuple[ForeignKeySnapshot, ...] = ()

    def get_column(self, name: str) -> ColumnSnapshot | None:
        """Ищет колонку по имени после trim входного значения."""
        normalized = name.strip()
        for item in self.columns:
            if item.name == normalized:
                return item
        return None

    def get_index(self, name: str) -> IndexSnapshot | None:
        """Ищет индекс по имени после trim входного значения."""
        normalized = name.strip()
        for item in self.indexes:
            if item.name == normalized:
                return item
        return None

    def has_unique_constraint_for_columns(self, columns: tuple[str, ...]) -> bool:
        """Проверяет наличие PK или unique-индекса по точному списку колонок."""
        if self.primary_key is not None and self.primary_key.columns == columns:
            return True
        for item in self.indexes:
            if item.is_unique and item.columns == columns:
                return True
        return False

    def get_foreign_key(self, name: str) -> ForeignKeySnapshot | None:
        """Ищет foreign key constraint по имени после trim входного значения."""
        normalized = name.strip()
        for item in self.foreign_keys:
            if item.name == normalized:
                return item
        return None


@dataclass(frozen=True, slots=True)
class PhysicalSchemaSnapshot:
    """Снимок всей физической PostgreSQL-схемы tenant."""

    schema_name: str
    tables: tuple[TableSnapshot, ...]

    def get_table(self, name: str) -> TableSnapshot | None:
        """Ищет таблицу по имени после trim входного значения."""
        normalized = name.strip()
        for item in self.tables:
            if item.name == normalized:
                return item
        return None
