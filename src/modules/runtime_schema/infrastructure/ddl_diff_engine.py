from __future__ import annotations

from src.modules.runtime_schema.infrastructure.contracts import DdlDiffEngineProtocol
from src.modules.runtime_schema.infrastructure.ddl_models import (
    ColumnToAdd,
    ColumnToDrop,
    DdlDiff,
    IndexToCreate,
    SchemaSnapshot,
    TableToCreate,
    TableToDrop,
)


class DdlDiffEngine(DdlDiffEngineProtocol):
    def diff(
        self,
        *,
        expected: SchemaSnapshot,
        actual: SchemaSnapshot,
        allow_destructive: bool = False,
    ) -> DdlDiff:
        expected_tables = expected.tables
        actual_tables = actual.tables

        tables_to_create: list[TableToCreate] = []
        columns_to_add: list[ColumnToAdd] = []
        indexes_to_create: list[IndexToCreate] = []
        tables_to_drop: list[TableToDrop] = []
        columns_to_drop: list[ColumnToDrop] = []

        for table_name, table in expected_tables.items():
            actual_table = actual_tables.get(table_name)
            if actual_table is None:
                tables_to_create.append(TableToCreate(table=table))
                for expected_index in table.indexes:
                    indexes_to_create.append(
                        IndexToCreate(
                            table_name=table_name,
                            index=expected_index,
                        )
                    )
                continue

            expected_columns_by_name = {column.name: column for column in table.columns}
            actual_columns_by_name = {column.name: column for column in actual_table.columns}

            for column_name, expected_column in expected_columns_by_name.items():
                if column_name not in actual_columns_by_name:
                    columns_to_add.append(
                        ColumnToAdd(
                            table_name=table_name,
                            column=expected_column,
                        )
                    )

            if allow_destructive:
                for column_name in actual_columns_by_name:
                    if column_name not in expected_columns_by_name and column_name not in {
                        "id",
                        "created_at",
                        "updated_at",
                    }:
                        columns_to_drop.append(
                            ColumnToDrop(
                                table_name=table_name,
                                column_name=column_name,
                            )
                        )

            actual_index_signatures = {
                (tuple(index.columns), index.unique) for index in actual_table.indexes
            }
            for expected_index in table.indexes:
                signature = (tuple(expected_index.columns), expected_index.unique)
                if signature not in actual_index_signatures:
                    indexes_to_create.append(
                        IndexToCreate(
                            table_name=table_name,
                            index=expected_index,
                        )
                    )

        if allow_destructive:
            for table_name in actual_tables:
                if table_name not in expected_tables:
                    tables_to_drop.append(TableToDrop(table_name=table_name))

        return DdlDiff(
            tables_to_create=tuple(tables_to_create),
            columns_to_add=tuple(columns_to_add),
            indexes_to_create=tuple(indexes_to_create),
            tables_to_drop=tuple(tables_to_drop),
            columns_to_drop=tuple(columns_to_drop),
        )


__all__ = ["DdlDiffEngine"]
