from __future__ import annotations

from src.modules.schema_registry.application.migration.operations import (
    AddColumnOperation,
    AddForeignKeyOperation,
    CreateIndexOperation,
    CreateSchemaOperation,
    CreateTableOperation,
    DropColumnOperation,
    DropForeignKeyOperation,
    DropIndexOperation,
    DropTableOperation,
)
from src.modules.schema_registry.application.migration.physical_schema_snapshot import (
    ColumnSnapshot,
    ForeignKeySnapshot,
    IndexSnapshot,
    PhysicalSchemaSnapshot,
    TableSnapshot,
)
from src.modules.schema_registry.application.migration.plan import MigrationPlan
from src.modules.schema_registry.application.migration.postgres_field_canonicalizer import (
    PostgresFieldCanonicalizer,
)
from src.modules.schema_registry.domain.error import UnsupportedSchemaChangeError
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed


class PostgresSchemaPlanService:
    def __init__(
        self,
        *,
        field_type_catalog: FieldTypeCatalog,
        postgres_field_canonicalizer: PostgresFieldCanonicalizer,
    ) -> None:
        self._field_type_catalog = field_type_catalog
        self._postgres_field_canonicalizer = postgres_field_canonicalizer

    def build_create_plan(
        self,
        *,
        schema_name: str,
        seed: SchemaSeed,
    ) -> MigrationPlan:
        plan = MigrationPlan()
        plan.add(CreateSchemaOperation(schema_name=schema_name))
        desired_schema = self._build_desired_schema(seed=seed, schema_name=schema_name)

        for table in desired_schema.tables:
            plan.add(
                CreateTableOperation(
                    schema_name=schema_name,
                    table_name=table.name,
                )
            )

        for table in desired_schema.tables:
            for column in table.columns:
                plan.add(
                    AddColumnOperation(
                        schema_name=schema_name,
                        table_name=table.name,
                        column_name=column.name,
                        sql_preset=column.sql_preset,
                        is_nullable=column.is_nullable,
                        default_value=column.default_value,
                    )
                )

        for table in desired_schema.tables:
            for index in table.indexes:
                plan.add(
                    CreateIndexOperation(
                        schema_name=schema_name,
                        table_name=table.name,
                        index_name=index.name,
                        columns=index.columns,
                        is_unique=index.is_unique,
                    )
                )

        for table in desired_schema.tables:
            for foreign_key in table.foreign_keys:
                plan.add(
                    AddForeignKeyOperation(
                        schema_name=schema_name,
                        table_name=table.name,
                        constraint_name=foreign_key.name,
                        column_name=foreign_key.source_columns[0],
                        target_schema_name=schema_name,
                        target_table_name=foreign_key.target_table_name,
                        target_column_name=foreign_key.target_columns[0],
                        on_delete=foreign_key.on_delete,
                    )
                )

        return plan

    def build_diff_plan(
        self,
        *,
        schema_name: str,
        seed: SchemaSeed,
        actual_schema: PhysicalSchemaSnapshot,
    ) -> MigrationPlan:
        plan = MigrationPlan()
        desired_schema = self._build_desired_schema(seed=seed, schema_name=schema_name)
        actual_tables = {table.name: table for table in actual_schema.tables}
        desired_tables = {table.name: table for table in desired_schema.tables}

        for actual_table in sorted(actual_schema.tables, key=lambda item: item.name):
            desired_table = desired_tables.get(actual_table.name)
            for foreign_key in sorted(
                actual_table.foreign_keys, key=lambda item: item.name
            ):
                desired_foreign_key = (
                    None
                    if desired_table is None
                    else desired_table.get_foreign_key(foreign_key.name)
                )
                if (
                    desired_table is None
                    or desired_foreign_key is None
                    or desired_foreign_key != foreign_key
                ):
                    plan.add_destructive(
                        DropForeignKeyOperation(
                            schema_name=schema_name,
                            table_name=actual_table.name,
                            constraint_name=foreign_key.name,
                        )
                    )

        for actual_table in sorted(actual_schema.tables, key=lambda item: item.name):
            desired_table = desired_tables.get(actual_table.name)
            for index in sorted(actual_table.indexes, key=lambda item: item.name):
                desired_index = (
                    None
                    if desired_table is None
                    else desired_table.get_index(index.name)
                )
                if (
                    desired_table is None
                    or desired_index is None
                    or desired_index != index
                ):
                    plan.add_destructive(
                        DropIndexOperation(
                            schema_name=schema_name,
                            index_name=index.name,
                        )
                    )

        for actual_table in sorted(actual_schema.tables, key=lambda item: item.name):
            desired_table = desired_tables.get(actual_table.name)
            if desired_table is None:
                continue
            for column in sorted(actual_table.columns, key=lambda item: item.name):
                desired_column = desired_table.get_column(column.name)
                if desired_column is None:
                    plan.add_destructive(
                        DropColumnOperation(
                            schema_name=schema_name,
                            table_name=actual_table.name,
                            column_name=column.name,
                        )
                    )
                    continue

                if (
                    desired_column.sql_preset != column.sql_preset
                    or desired_column.is_nullable != column.is_nullable
                    or desired_column.default_value != column.default_value
                ):
                    raise UnsupportedSchemaChangeError(
                        "Unsupported retained column change "
                        f"for '{actual_table.name}.{column.name}'."
                    )

        for actual_table in sorted(actual_schema.tables, key=lambda item: item.name):
            if actual_table.name not in desired_tables:
                plan.add_destructive(
                    DropTableOperation(
                        schema_name=schema_name,
                        table_name=actual_table.name,
                    )
                )

        for desired_table in desired_schema.tables:
            if desired_table.name not in actual_tables:
                plan.add(
                    CreateTableOperation(
                        schema_name=schema_name,
                        table_name=desired_table.name,
                    )
                )

        for desired_table in desired_schema.tables:
            actual_table = actual_tables.get(desired_table.name)
            for column in desired_table.columns:
                if (
                    actual_table is not None
                    and actual_table.get_column(column.name) is not None
                ):
                    continue
                plan.add(
                    AddColumnOperation(
                        schema_name=schema_name,
                        table_name=desired_table.name,
                        column_name=column.name,
                        sql_preset=column.sql_preset,
                        is_nullable=column.is_nullable,
                        default_value=column.default_value,
                    )
                )

        for desired_table in desired_schema.tables:
            actual_table = actual_tables.get(desired_table.name)
            for index in desired_table.indexes:
                actual_index = (
                    None if actual_table is None else actual_table.get_index(index.name)
                )
                if actual_index == index:
                    continue
                plan.add(
                    CreateIndexOperation(
                        schema_name=schema_name,
                        table_name=desired_table.name,
                        index_name=index.name,
                        columns=index.columns,
                        is_unique=index.is_unique,
                    )
                )

        for desired_table in desired_schema.tables:
            actual_table = actual_tables.get(desired_table.name)
            for foreign_key in desired_table.foreign_keys:
                actual_foreign_key = (
                    None
                    if actual_table is None
                    else actual_table.get_foreign_key(foreign_key.name)
                )
                if actual_foreign_key == foreign_key:
                    continue
                plan.add(
                    AddForeignKeyOperation(
                        schema_name=schema_name,
                        table_name=desired_table.name,
                        constraint_name=foreign_key.name,
                        column_name=foreign_key.source_columns[0],
                        target_schema_name=schema_name,
                        target_table_name=foreign_key.target_table_name,
                        target_column_name=foreign_key.target_columns[0],
                        on_delete=foreign_key.on_delete,
                    )
                )

        return plan

    def _build_desired_schema(
        self,
        *,
        seed: SchemaSeed,
        schema_name: str,
    ) -> PhysicalSchemaSnapshot:
        tables: list[TableSnapshot] = []
        for object_seed in seed.objects:
            columns = tuple(
                self._build_column_snapshot(field_seed)
                for field_seed in object_seed.fields
            )
            indexes = tuple(
                IndexSnapshot(
                    name=index_seed.name,
                    columns=index_seed.fields,
                    is_unique=index_seed.is_unique,
                )
                for index_seed in object_seed.indexes
            )
            foreign_keys: list[ForeignKeySnapshot] = []
            for relation_seed in object_seed.relations:
                target_object = seed.get_object(relation_seed.target_object)
                if target_object is None:
                    raise UnsupportedSchemaChangeError(
                        f"Target object '{relation_seed.target_object}' not found in seed."
                    )
                foreign_keys.append(
                    ForeignKeySnapshot(
                        name=relation_seed.name,
                        source_columns=(relation_seed.source_field,),
                        target_table_name=target_object.plural_name,
                        target_columns=(relation_seed.target_field,),
                        on_delete=self._normalize_on_delete(relation_seed.on_delete),
                    )
                )
            tables.append(
                TableSnapshot(
                    name=object_seed.plural_name,
                    columns=columns,
                    indexes=indexes,
                    foreign_keys=tuple(foreign_keys),
                )
            )
        return PhysicalSchemaSnapshot(schema_name=schema_name, tables=tuple(tables))

    def _build_column_snapshot(self, field_seed) -> ColumnSnapshot:
        field_type = self._field_type_catalog.from_seed_type(field_seed.type)
        sql_preset = self._postgres_field_canonicalizer.sql_preset_from_field_type(
            field_type
        )
        return ColumnSnapshot(
            name=field_seed.name,
            sql_preset=sql_preset,
            is_nullable=field_seed.is_nullable,
            default_value=self._postgres_field_canonicalizer.normalize_seed_default(
                raw_default=field_seed.default,
                sql_preset=sql_preset,
            ),
        )

    @staticmethod
    def _normalize_on_delete(value: str) -> str:
        mapping = {
            "restrict": "restrict",
            "cascade": "cascade",
            "set null": "set null",
            "set_null": "set null",
            "no action": "no action",
            "no_action": "no action",
        }
        return mapping.get(value.strip().lower(), "restrict")
