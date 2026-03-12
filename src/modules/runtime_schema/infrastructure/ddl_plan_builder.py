from __future__ import annotations

from src.modules.runtime_schema.infrastructure.contracts import DdlPlanBuilderProtocol
from src.modules.runtime_schema.infrastructure.ddl_models import (
    ColumnSpec,
    DdlDiff,
    DdlOperation,
    DdlOperationKind,
    DdlPlan,
    TableToCreate,
)


class DdlPlanBuilder(DdlPlanBuilderProtocol):
    def __init__(self, *, dialect_name: str):
        self._dialect_name = dialect_name.lower()

    def build(self, *, schema: str, diff: DdlDiff) -> DdlPlan:
        operations: list[DdlOperation] = []

        ordered_tables_to_create = self._order_tables_to_create(diff.tables_to_create)
        for item in ordered_tables_to_create:
            sql = self._build_create_table_sql(
                schema=schema,
                table_name=item.table.name,
                columns=item.table.columns,
            )
            operations.append(
                DdlOperation(
                    key=f"create_table:{item.table.name}",
                    kind=DdlOperationKind.CREATE_TABLE,
                    sql=sql,
                )
            )

        for item in diff.columns_to_add:
            sql = (
                f"ALTER TABLE {self._qualified_table(schema=schema, table_name=item.table_name)} "
                f"ADD COLUMN {self._build_column_sql(item.column, schema=schema)}"
            )
            operations.append(
                DdlOperation(
                    key=f"add_column:{item.table_name}.{item.column.name}",
                    kind=DdlOperationKind.ADD_COLUMN,
                    sql=sql,
                )
            )

        for item in diff.indexes_to_create:
            unique_sql = "UNIQUE " if item.index.unique else ""
            columns_sql = ", ".join(self._quote_identifier(col) for col in item.index.columns)
            sql = (
                f"CREATE {unique_sql}INDEX IF NOT EXISTS {self._quote_identifier(item.index.name)} "
                f"ON {self._qualified_table(schema=schema, table_name=item.table_name)} ({columns_sql})"
            )
            operations.append(
                DdlOperation(
                    key=f"create_index:{item.index.name}",
                    kind=DdlOperationKind.CREATE_INDEX,
                    sql=sql,
                )
            )

        for item in diff.columns_to_drop:
            if self._dialect_name == "sqlite":
                continue
            sql = (
                f"ALTER TABLE {self._qualified_table(schema=schema, table_name=item.table_name)} "
                f"DROP COLUMN {self._quote_identifier(item.column_name)}"
            )
            operations.append(
                DdlOperation(
                    key=f"drop_column:{item.table_name}.{item.column_name}",
                    kind=DdlOperationKind.DROP_COLUMN,
                    sql=sql,
                )
            )

        for item in diff.tables_to_drop:
            sql = (
                f"DROP TABLE IF EXISTS {self._qualified_table(schema=schema, table_name=item.table_name)}"
            )
            operations.append(
                DdlOperation(
                    key=f"drop_table:{item.table_name}",
                    kind=DdlOperationKind.DROP_TABLE,
                    sql=sql,
                )
            )

        return DdlPlan(operations=tuple(operations))

    def build_rename_table_operation(
        self,
        *,
        schema: str,
        old_table_name: str,
        new_table_name: str,
    ) -> DdlOperation:
        sql = (
            f"ALTER TABLE {self._qualified_table(schema=schema, table_name=old_table_name)} "
            f"RENAME TO {self._quote_identifier(self._physical_table(schema=schema, table_name=new_table_name))}"
        )
        return DdlOperation(
            key=f"rename_table:{old_table_name}->{new_table_name}",
            kind=DdlOperationKind.RENAME_TABLE,
            sql=sql,
        )

    def _build_create_table_sql(
        self,
        *,
        schema: str,
        table_name: str,
        columns: tuple[ColumnSpec, ...],
    ) -> str:
        column_sql = ", ".join(
            self._build_column_sql(column, schema=schema) for column in columns
        )
        return (
            f"CREATE TABLE IF NOT EXISTS {self._qualified_table(schema=schema, table_name=table_name)} "
            f"({column_sql})"
        )

    def _build_column_sql(self, column: ColumnSpec, *, schema: str | None = None) -> str:
        sql_type = self._map_sql_type(column.sql_type)
        nullable_sql = "" if column.nullable else " NOT NULL"
        pk_sql = " PRIMARY KEY" if column.is_primary_key else ""
        default_sql = f" DEFAULT {column.default_sql}" if column.default_sql else ""
        reference_sql = ""
        if column.references_table and column.references_column:
            target_table = column.references_table
            if self._dialect_name != "postgresql" and schema is not None:
                target_table = self._physical_table(
                    schema=schema,
                    table_name=column.references_table,
                )
            reference_sql = (
                f" REFERENCES {self._quote_identifier(target_table)}"
                f"({self._quote_identifier(column.references_column)})"
            )
            if column.on_delete:
                reference_sql += (
                    f" ON DELETE {self._map_on_delete_action(column.on_delete)}"
                )
        return (
            f"{self._quote_identifier(column.name)} {sql_type}{pk_sql}{nullable_sql}{default_sql}{reference_sql}"
        )

    @staticmethod
    def _order_tables_to_create(
        tables_to_create: tuple[TableToCreate, ...],
    ) -> tuple[TableToCreate, ...]:
        if len(tables_to_create) <= 1:
            return tables_to_create

        items_by_name = {item.table.name: item for item in tables_to_create}
        dependencies: dict[str, set[str]] = {}
        for item in tables_to_create:
            table_name = item.table.name
            refs = {
                column.references_table
                for column in item.table.columns
                if column.references_table is not None
                and column.references_table in items_by_name
                and column.references_table != table_name
            }
            dependencies[table_name] = refs

        in_degree = {table_name: 0 for table_name in items_by_name}
        for table_name, refs in dependencies.items():
            in_degree[table_name] = len(refs)

        queue = sorted(
            [table_name for table_name, degree in in_degree.items() if degree == 0]
        )
        ordered_names: list[str] = []

        while queue:
            current = queue.pop(0)
            ordered_names.append(current)
            for table_name, refs in dependencies.items():
                if current not in refs:
                    continue
                refs.remove(current)
                in_degree[table_name] -= 1
                if in_degree[table_name] == 0:
                    queue.append(table_name)
            queue.sort()

        if len(ordered_names) != len(items_by_name):
            # fallback for cycles or malformed refs: keep deterministic original order
            return tables_to_create

        return tuple(items_by_name[table_name] for table_name in ordered_names)

    def _map_sql_type(self, sql_type: str) -> str:
        normalized = sql_type.strip().lower()
        if normalized.startswith("varchar("):
            return normalized.upper()

        if normalized == "uuid":
            return "UUID" if self._dialect_name == "postgresql" else "TEXT"
        if normalized == "timestamp_tz":
            if self._dialect_name == "postgresql":
                return "TIMESTAMP WITH TIME ZONE"
            return "TEXT"
        if normalized == "json":
            return "JSONB" if self._dialect_name == "postgresql" else "JSON"
        if normalized == "bigint":
            return "BIGINT" if self._dialect_name == "postgresql" else "INTEGER"
        if normalized == "boolean":
            return "BOOLEAN" if self._dialect_name == "postgresql" else "INTEGER"
        if normalized == "text":
            return "TEXT"
        return normalized.upper()

    def _qualified_table(self, *, schema: str, table_name: str) -> str:
        physical = self._physical_table(schema=schema, table_name=table_name)
        if self._dialect_name == "postgresql":
            return f"{self._quote_identifier(schema)}.{self._quote_identifier(physical)}"
        return self._quote_identifier(physical)

    def _physical_table(self, *, schema: str, table_name: str) -> str:
        if self._dialect_name == "postgresql":
            return table_name
        return f"{schema}__{table_name}"

    @staticmethod
    def _map_on_delete_action(value: str) -> str:
        normalized = value.strip().lower()
        if normalized == "set_null":
            return "SET NULL"
        return normalized.upper()

    @staticmethod
    def _quote_identifier(value: str) -> str:
        return '"' + value.replace('"', '""') + '"'


__all__ = ["DdlPlanBuilder"]
