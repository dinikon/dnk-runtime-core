from __future__ import annotations

from collections import defaultdict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.schema_registry.application.ports.tenant_schema_inspector import (
    TenantSchemaInspectorPort,
)
from src.modules.schema_registry.application.migration.physical_schema_snapshot import (
    ColumnSnapshot,
    ForeignKeySnapshot,
    IndexSnapshot,
    PhysicalSchemaSnapshot,
    PrimaryKeySnapshot,
    TableSnapshot,
)
from src.modules.schema_registry.application.migration.postgres_field_canonicalizer import (
    PostgresFieldCanonicalizer,
)
from src.modules.schema_registry.domain.error import UnsupportedSchemaBackendError


class PostgresTenantSchemaInspector(TenantSchemaInspectorPort):
    """PostgreSQL-адаптер, читающий фактическую структуру tenant-схемы."""

    def __init__(
        self,
        session: AsyncSession,
        postgres_field_canonicalizer: PostgresFieldCanonicalizer,
    ) -> None:
        """Инициализирует inspector SQLAlchemy-сессией и SQL-канонизатором типов."""
        self._session = session
        self._postgres_field_canonicalizer = postgres_field_canonicalizer

    async def schema_exists(self, *, schema_name: str) -> bool:
        """Проверяет наличие schema_name через information_schema."""
        self._ensure_postgres()
        result = await self._session.scalar(
            text("""
                SELECT EXISTS(
                    SELECT 1
                    FROM information_schema.schemata
                    WHERE schema_name = :schema_name
                )
                """),
            {"schema_name": schema_name},
        )
        return bool(result)

    async def inspect(self, *, schema_name: str) -> PhysicalSchemaSnapshot:
        """Собирает snapshot схемы из таблиц, колонок, индексов и foreign keys."""
        self._ensure_postgres()
        tables = await self._load_tables(schema_name=schema_name)
        columns = await self._load_columns(schema_name=schema_name)
        primary_keys = await self._load_primary_keys(schema_name=schema_name)
        indexes = await self._load_indexes(schema_name=schema_name)
        foreign_keys = await self._load_foreign_keys(schema_name=schema_name)

        snapshots: list[TableSnapshot] = []
        for table_name in sorted(tables):
            snapshots.append(
                TableSnapshot(
                    name=table_name,
                    columns=tuple(columns.get(table_name, [])),
                    primary_key=primary_keys.get(table_name),
                    indexes=tuple(indexes.get(table_name, [])),
                    foreign_keys=tuple(foreign_keys.get(table_name, [])),
                )
            )
        return PhysicalSchemaSnapshot(schema_name=schema_name, tables=tuple(snapshots))

    async def table_has_rows(self, *, schema_name: str, table_name: str) -> bool:
        """Проверяет наличие хотя бы одной строки в таблице tenant-схемы."""
        self._ensure_postgres()
        result = await self._session.scalar(
            text(
                "SELECT EXISTS ("
                "SELECT 1 FROM "
                f"{self._qualified_table(schema_name, table_name)} "
                "LIMIT 1)"
            )
        )
        return bool(result)

    async def column_has_non_null_values(
        self,
        *,
        schema_name: str,
        table_name: str,
        column_name: str,
    ) -> bool:
        """Проверяет наличие хотя бы одного non-null значения в колонке."""
        self._ensure_postgres()
        result = await self._session.scalar(
            text(
                "SELECT EXISTS ("
                "SELECT 1 FROM "
                f"{self._qualified_table(schema_name, table_name)} "
                f"WHERE {self._qi(column_name)} IS NOT NULL "
                "LIMIT 1)"
            )
        )
        return bool(result)

    def _ensure_postgres(self) -> None:
        """Проверяет, что текущий SQLAlchemy bind указывает на PostgreSQL dialect."""
        bind = self._session.get_bind()
        if bind.dialect.name != "postgresql":
            raise UnsupportedSchemaBackendError(
                "schema_registry PostgreSQL adapters require a PostgreSQL backend."
            )

    async def _load_tables(self, *, schema_name: str) -> tuple[str, ...]:
        """Загружает имена base tables tenant-схемы из information_schema."""
        rows = (
            await self._session.execute(
                text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = :schema_name
                      AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                    """),
                {"schema_name": schema_name},
            )
        ).all()
        return tuple(row.table_name for row in rows)

    async def _load_columns(
        self,
        *,
        schema_name: str,
    ) -> dict[str, list[ColumnSnapshot]]:
        """Загружает колонки из pg_catalog и канонизирует тип/default каждой."""
        rows = (
            await self._session.execute(
                text("""
                    SELECT
                        cls.relname AS table_name,
                        attr.attname AS column_name,
                        format_type(attr.atttypid, attr.atttypmod) AS format_type,
                        NOT attr.attnotnull AS is_nullable,
                        pg_get_expr(def.adbin, def.adrelid) AS column_default
                    FROM pg_attribute attr
                    JOIN pg_class cls ON cls.oid = attr.attrelid
                    JOIN pg_namespace nsp ON nsp.oid = cls.relnamespace
                    LEFT JOIN pg_attrdef def
                      ON def.adrelid = attr.attrelid
                     AND def.adnum = attr.attnum
                    WHERE nsp.nspname = :schema_name
                      AND cls.relkind = 'r'
                      AND attr.attnum > 0
                      AND NOT attr.attisdropped
                    ORDER BY cls.relname, attr.attnum
                    """),
                {"schema_name": schema_name},
            )
        ).all()
        grouped: dict[str, list[ColumnSnapshot]] = defaultdict(list)
        for row in rows:
            sql_preset = (
                self._postgres_field_canonicalizer.sql_preset_from_postgres_type(
                    row.format_type
                )
            )
            grouped[row.table_name].append(
                ColumnSnapshot(
                    name=row.column_name,
                    sql_preset=sql_preset,
                    is_nullable=bool(row.is_nullable),
                    default_value=self._postgres_field_canonicalizer.normalize_postgres_default(
                        raw_default=row.column_default,
                        sql_preset=sql_preset,
                    ),
                )
            )
        return grouped

    async def _load_indexes(
        self,
        *,
        schema_name: str,
    ) -> dict[str, list[IndexSnapshot]]:
        """Загружает non-primary индексы и их упорядоченные колонки."""
        rows = (
            await self._session.execute(
                text("""
                    SELECT
                        tab.relname AS table_name,
                        idx.relname AS index_name,
                        ind.indisunique AS is_unique,
                        array_agg(att.attname ORDER BY ord.ordinality) AS columns
                    FROM pg_class tab
                    JOIN pg_namespace nsp ON nsp.oid = tab.relnamespace
                    JOIN pg_index ind ON ind.indrelid = tab.oid
                    JOIN pg_class idx ON idx.oid = ind.indexrelid
                    JOIN LATERAL unnest(ind.indkey) WITH ORDINALITY AS ord(attnum, ordinality)
                      ON TRUE
                    JOIN pg_attribute att
                      ON att.attrelid = tab.oid
                     AND att.attnum = ord.attnum
                    WHERE nsp.nspname = :schema_name
                      AND tab.relkind = 'r'
                      AND NOT ind.indisprimary
                    GROUP BY tab.relname, idx.relname, ind.indisunique
                    ORDER BY tab.relname, idx.relname
                    """),
                {"schema_name": schema_name},
            )
        ).all()
        grouped: dict[str, list[IndexSnapshot]] = defaultdict(list)
        for row in rows:
            grouped[row.table_name].append(
                IndexSnapshot(
                    name=row.index_name,
                    columns=tuple(row.columns),
                    is_unique=bool(row.is_unique),
                )
            )
        return grouped

    async def _load_primary_keys(
        self,
        *,
        schema_name: str,
    ) -> dict[str, PrimaryKeySnapshot]:
        """Загружает primary key constraints и их упорядоченные колонки."""
        rows = (
            await self._session.execute(
                text("""
                    SELECT
                        tab.relname AS table_name,
                        con.conname AS constraint_name,
                        array_agg(att.attname ORDER BY ord.ordinality) AS columns
                    FROM pg_constraint con
                    JOIN pg_class tab ON tab.oid = con.conrelid
                    JOIN pg_namespace nsp ON nsp.oid = tab.relnamespace
                    JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS ord(attnum, ordinality)
                      ON TRUE
                    JOIN pg_attribute att
                      ON att.attrelid = tab.oid
                     AND att.attnum = ord.attnum
                    WHERE nsp.nspname = :schema_name
                      AND tab.relkind = 'r'
                      AND con.contype = 'p'
                    GROUP BY tab.relname, con.conname
                    ORDER BY tab.relname
                    """),
                {"schema_name": schema_name},
            )
        ).all()
        return {
            row.table_name: PrimaryKeySnapshot(
                name=row.constraint_name,
                columns=tuple(row.columns),
            )
            for row in rows
        }

    async def _load_foreign_keys(
        self,
        *,
        schema_name: str,
    ) -> dict[str, list[ForeignKeySnapshot]]:
        """Загружает foreign key constraints и нормализует on_delete действие."""
        rows = (
            await self._session.execute(
                text("""
                    SELECT
                        src.relname AS table_name,
                        con.conname AS constraint_name,
                        array_agg(src_att.attname ORDER BY src_ord.ordinality) AS source_columns,
                        tgt.relname AS target_table_name,
                        array_agg(tgt_att.attname ORDER BY src_ord.ordinality) AS target_columns,
                        CASE con.confdeltype
                            WHEN 'a' THEN 'no_action'
                            WHEN 'r' THEN 'restrict'
                            WHEN 'c' THEN 'cascade'
                            WHEN 'n' THEN 'set_null'
                            WHEN 'd' THEN 'set default'
                        END AS on_delete
                    FROM pg_constraint con
                    JOIN pg_class src ON src.oid = con.conrelid
                    JOIN pg_namespace nsp ON nsp.oid = src.relnamespace
                    JOIN pg_class tgt ON tgt.oid = con.confrelid
                    JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS src_ord(attnum, ordinality)
                      ON TRUE
                    JOIN pg_attribute src_att
                      ON src_att.attrelid = src.oid
                     AND src_att.attnum = src_ord.attnum
                    JOIN LATERAL unnest(con.confkey) WITH ORDINALITY AS tgt_ord(attnum, ordinality)
                      ON tgt_ord.ordinality = src_ord.ordinality
                    JOIN pg_attribute tgt_att
                      ON tgt_att.attrelid = tgt.oid
                     AND tgt_att.attnum = tgt_ord.attnum
                    WHERE nsp.nspname = :schema_name
                      AND con.contype = 'f'
                    GROUP BY src.relname, con.conname, tgt.relname, con.confdeltype
                    ORDER BY src.relname, con.conname
                    """),
                {"schema_name": schema_name},
            )
        ).all()
        grouped: dict[str, list[ForeignKeySnapshot]] = defaultdict(list)
        for row in rows:
            grouped[row.table_name].append(
                ForeignKeySnapshot(
                    name=row.constraint_name,
                    source_columns=tuple(row.source_columns),
                    target_table_name=row.target_table_name,
                    target_columns=tuple(row.target_columns),
                    on_delete=row.on_delete,
                )
            )
        return grouped

    @staticmethod
    def _qi(identifier: str) -> str:
        """Кавычит PostgreSQL-идентификатор для запросов к tenant-схеме."""
        return f'"{identifier.replace(chr(34), chr(34) + chr(34))}"'

    @classmethod
    def _qualified_table(cls, schema_name: str, table_name: str) -> str:
        """Возвращает fully-qualified имя таблицы schema.table."""
        return f"{cls._qi(schema_name)}.{cls._qi(table_name)}"
