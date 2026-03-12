from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_schema.infrastructure.contracts import SchemaIntrospectorProtocol
from src.modules.runtime_schema.infrastructure.ddl_models import (
    ColumnSpec,
    IndexSpec,
    SchemaSnapshot,
    TableSpec,
)


class SqlAlchemySchemaIntrospector(SchemaIntrospectorProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def introspect(self, *, schema: str) -> SchemaSnapshot:
        bind = self._session.get_bind()
        dialect_name = bind.dialect.name.lower()
        payload = await self._session.run_sync(
            self._collect_schema_payload,
            schema,
            dialect_name,
        )
        return self._to_snapshot(payload)

    @staticmethod
    def _collect_schema_payload(sync_session, schema: str, dialect_name: str) -> dict[str, dict]:
        inspector = inspect(sync_session.connection())
        if dialect_name == "postgresql":
            physical_tables = inspector.get_table_names(schema=schema)
            logical_to_physical = {name: name for name in physical_tables}
            schema_name = schema
        else:
            table_prefix = f"{schema}__"
            physical_tables = [
                table_name
                for table_name in inspector.get_table_names()
                if table_name.startswith(table_prefix)
            ]
            logical_to_physical = {
                table_name[len(table_prefix):]: table_name for table_name in physical_tables
            }
            schema_name = None

        result: dict[str, dict] = {}
        for logical_table_name, physical_table_name in logical_to_physical.items():
            columns_payload = inspector.get_columns(physical_table_name, schema=schema_name)
            pk_payload = inspector.get_pk_constraint(physical_table_name, schema=schema_name)
            pk_columns = set(pk_payload.get("constrained_columns") or [])
            indexes_payload = inspector.get_indexes(physical_table_name, schema=schema_name)

            result[logical_table_name] = {
                "columns": columns_payload,
                "primary_keys": pk_columns,
                "indexes": indexes_payload,
            }
        return result

    @staticmethod
    def _to_snapshot(payload: dict[str, dict]) -> SchemaSnapshot:
        tables: dict[str, TableSpec] = {}
        for table_name, table_payload in payload.items():
            columns: list[ColumnSpec] = []
            for column_payload in table_payload["columns"]:
                column_name = str(column_payload["name"])
                sql_type = SqlAlchemySchemaIntrospector._normalize_sql_type(
                    str(column_payload.get("type", "text"))
                )
                columns.append(
                    ColumnSpec(
                        name=column_name,
                        sql_type=sql_type,
                        nullable=bool(column_payload.get("nullable", True)),
                        is_primary_key=column_name in table_payload["primary_keys"],
                    )
                )

            indexes: list[IndexSpec] = []
            for index_payload in table_payload["indexes"]:
                columns_raw = index_payload.get("column_names") or []
                columns_tuple = tuple(str(col) for col in columns_raw if col is not None)
                if not columns_tuple:
                    continue
                index_name = str(
                    index_payload.get("name")
                    or f"idx_{table_name}_{'_'.join(columns_tuple)}"
                )
                indexes.append(
                    IndexSpec(
                        name=index_name,
                        columns=columns_tuple,
                        unique=bool(index_payload.get("unique", False)),
                    )
                )

            tables[table_name] = TableSpec(
                name=table_name,
                columns=tuple(columns),
                indexes=tuple(indexes),
            )
        return SchemaSnapshot(tables=tables)

    @staticmethod
    def _normalize_sql_type(value: str) -> str:
        normalized = value.strip().lower()
        if "character varying" in normalized:
            return "varchar(255)"
        if normalized.startswith("varchar"):
            return normalized
        if "timestamp" in normalized:
            return "timestamp_tz"
        if "uuid" in normalized:
            return "uuid"
        if "json" in normalized:
            return "json"
        if "bool" in normalized:
            return "boolean"
        if "bigint" in normalized:
            return "bigint"
        if normalized in {"integer", "int"}:
            return "bigint"
        return "text"


__all__ = ["SqlAlchemySchemaIntrospector"]
