from __future__ import annotations

from dataclasses import dataclass

from src.modules.schema_registry.application.migration.operations import (
    AddColumnOperation,
    AlterColumnDefaultOperation,
    AlterColumnNullableOperation,
    AlterColumnTypeOperation,
    AddForeignKeyOperation,
    AddPrimaryKeyOperation,
    CreateIndexOperation,
    CreateSchemaOperation,
    CreateTableOperation,
    DropColumnOperation,
    DropForeignKeyOperation,
    DropIndexOperation,
    DropPrimaryKeyOperation,
    DropTableOperation,
)
from src.modules.schema_registry.application.migration.physical_schema_snapshot import (
    ColumnSnapshot,
    ForeignKeySnapshot,
    IndexSnapshot,
    PhysicalSchemaSnapshot,
    PrimaryKeySnapshot,
    TableSnapshot,
)
from src.modules.schema_registry.application.migration.plan import MigrationPlan
from src.modules.schema_registry.application.migration.postgres_field_canonicalizer import (
    PostgresFieldCanonicalizer,
)
from src.modules.schema_registry.application.migration.schema_naming_strategy import (
    SchemaNamingStrategy,
)
from src.modules.schema_registry.application.migration.sql_type_preset import (
    SqlTypePresetEnum,
)
from src.modules.schema_registry.domain.error import UnsupportedSchemaChangeError
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.domain.object.naming import has_custom_object_prefix
from src.modules.schema_registry.domain.seed.field_seed import FieldSeed
from src.modules.schema_registry.domain.seed.object_seed import ObjectSeed
from src.modules.schema_registry.domain.seed.relation_type import RelationTypeEnum
from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed
from src.modules.schema_registry.domain.seed.validated_schema_spec import (
    ValidatedFieldSpec,
    ValidatedObjectSpec,
    ValidatedRelationSpec,
    ValidatedSchemaSpec,
)


@dataclass(frozen=True, slots=True)
class PreservedSchemaArtifacts:
    """Политика для metadata-managed артефактов вне текущего seed."""

    table_names: frozenset[str] = frozenset()
    column_names: frozenset[tuple[str, str]] = frozenset()
    index_names: frozenset[str] = frozenset()
    foreign_keys: frozenset[tuple[str, str]] = frozenset()
    removed_table_names: frozenset[str] = frozenset()
    removed_column_names: frozenset[tuple[str, str]] = frozenset()
    removed_index_names: frozenset[str] = frozenset()
    removed_foreign_keys: frozenset[tuple[str, str]] = frozenset()

    def has_table(self, table_name: str) -> bool:
        """Проверяет, нужно ли сохранить таблицу даже если ее нет в desired."""
        return table_name in self.table_names

    def has_column(self, table_name: str, column_name: str) -> bool:
        """Проверяет, нужно ли сохранить metadata-managed колонку."""
        return (table_name, column_name) in self.column_names

    def has_index(self, index_name: str) -> bool:
        """Проверяет, нужно ли сохранить индекс даже если его нет в desired."""
        return index_name in self.index_names

    def has_foreign_key(self, table_name: str, constraint_name: str) -> bool:
        """Проверяет, нужно ли сохранить FK даже если его нет в desired."""
        return (table_name, constraint_name) in self.foreign_keys

    def removes_table(self, table_name: str) -> bool:
        """Проверяет, нужно ли удалить retired relation table."""
        return table_name in self.removed_table_names

    def removes_column(self, table_name: str, column_name: str) -> bool:
        """Проверяет, нужно ли удалить retired relation column."""
        return (table_name, column_name) in self.removed_column_names

    def removes_index(self, index_name: str) -> bool:
        """Проверяет, нужно ли удалить retired relation index."""
        return index_name in self.removed_index_names

    def removes_foreign_key(self, table_name: str, constraint_name: str) -> bool:
        """Проверяет, нужно ли удалить retired relation FK."""
        return (table_name, constraint_name) in self.removed_foreign_keys


class PostgresSchemaPlanService:
    """Строит PostgreSQL migration plan из seed/spec и снимка физической схемы."""

    def __init__(
        self,
        *,
        field_type_catalog: FieldTypeCatalog,
        postgres_field_canonicalizer: PostgresFieldCanonicalizer,
    ) -> None:
        """Инициализирует сервис правилами field-типов и SQL-канонизации."""
        self._field_type_catalog = field_type_catalog
        self._postgres_field_canonicalizer = postgres_field_canonicalizer

    def build_create_plan(
        self,
        *,
        schema_name: str,
        seed: SchemaSeed | ValidatedSchemaSpec,
    ) -> MigrationPlan:
        """Строит полный план создания схемы, таблиц, колонок, индексов и FK."""
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
            if table.primary_key is None:
                continue
            plan.add(
                AddPrimaryKeyOperation(
                    schema_name=schema_name,
                    table_name=table.name,
                    constraint_name=table.primary_key.name,
                    columns=table.primary_key.columns,
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
        seed: SchemaSeed | ValidatedSchemaSpec,
        actual_schema: PhysicalSchemaSnapshot,
        preserved_artifacts: PreservedSchemaArtifacts | None = None,
    ) -> MigrationPlan:
        """Строит diff-план между желаемой и фактической схемой PostgreSQL.

        Порядок операций важен: сначала снимаются FK и индексы, которые могут
        блокировать изменение таблиц, затем добавляются недостающие элементы.
        Небезопасные изменения retained-колонок явно отклоняются.
        """
        plan = MigrationPlan()
        preserved = preserved_artifacts or PreservedSchemaArtifacts()
        desired_schema = self._build_desired_schema(seed=seed, schema_name=schema_name)
        actual_tables = {table.name: table for table in actual_schema.tables}
        desired_tables = {table.name: table for table in desired_schema.tables}
        alter_type_operations: list[AlterColumnTypeOperation] = []
        alter_default_operations: list[AlterColumnDefaultOperation] = []
        alter_nullable_operations: list[AlterColumnNullableOperation] = []

        for actual_table in sorted(actual_schema.tables, key=lambda item: item.name):
            desired_table = desired_tables.get(actual_table.name)
            is_custom_table = self._is_custom_table(actual_table.name)
            if (
                desired_table is None
                and is_custom_table
                and not any(
                    preserved.removes_foreign_key(actual_table.name, item.name)
                    for item in actual_table.foreign_keys
                )
            ):
                continue
            for foreign_key in sorted(
                actual_table.foreign_keys, key=lambda item: item.name
            ):
                desired_foreign_key = (
                    None
                    if desired_table is None
                    else desired_table.get_foreign_key(foreign_key.name)
                )
                should_remove = preserved.removes_foreign_key(
                    actual_table.name,
                    foreign_key.name,
                )
                if should_remove or (
                    not is_custom_table
                    and (
                        desired_table is None
                        or desired_foreign_key is None
                        or desired_foreign_key != foreign_key
                    )
                ):
                    if (
                        preserved.has_foreign_key(
                            actual_table.name,
                            foreign_key.name,
                        )
                        and not should_remove
                    ):
                        continue
                    plan.add_destructive(
                        DropForeignKeyOperation(
                            schema_name=schema_name,
                            table_name=actual_table.name,
                            constraint_name=foreign_key.name,
                        )
                    )

        for actual_table in sorted(actual_schema.tables, key=lambda item: item.name):
            desired_table = desired_tables.get(actual_table.name)
            is_custom_table = self._is_custom_table(actual_table.name)
            if (
                desired_table is None
                and is_custom_table
                and not any(
                    preserved.removes_index(item.name) for item in actual_table.indexes
                )
            ):
                continue
            for index in sorted(actual_table.indexes, key=lambda item: item.name):
                desired_index = (
                    None
                    if desired_table is None
                    else desired_table.get_index(index.name)
                )
                should_remove = preserved.removes_index(index.name)
                if should_remove or (
                    not is_custom_table
                    and (
                        desired_table is None
                        or desired_index is None
                        or desired_index != index
                    )
                ):
                    if preserved.has_index(index.name) and not should_remove:
                        continue
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
            if actual_table.primary_key == desired_table.primary_key:
                continue
            if actual_table.primary_key is None:
                continue
            if desired_table.primary_key is None:
                if preserved.has_table(actual_table.name):
                    continue
                plan.add_destructive(
                    DropPrimaryKeyOperation(
                        schema_name=schema_name,
                        table_name=actual_table.name,
                        constraint_name=actual_table.primary_key.name,
                    )
                )
                continue
            raise UnsupportedSchemaChangeError(
                "Unsupported retained primary key change " f"for '{actual_table.name}'."
            )

        for actual_table in sorted(actual_schema.tables, key=lambda item: item.name):
            desired_table = desired_tables.get(actual_table.name)
            if desired_table is None:
                for column in sorted(actual_table.columns, key=lambda item: item.name):
                    if not preserved.removes_column(
                        actual_table.name,
                        column.name,
                    ):
                        continue
                    plan.add_destructive(
                        DropColumnOperation(
                            schema_name=schema_name,
                            table_name=actual_table.name,
                            column_name=column.name,
                        )
                    )
                continue
            for column in sorted(actual_table.columns, key=lambda item: item.name):
                desired_column = desired_table.get_column(column.name)
                if desired_column is None:
                    if preserved.has_column(actual_table.name, column.name):
                        continue
                    plan.add_destructive(
                        DropColumnOperation(
                            schema_name=schema_name,
                            table_name=actual_table.name,
                            column_name=column.name,
                        )
                    )
                    continue

                if desired_column.sql_preset != column.sql_preset:
                    if self._is_supported_timestamp_utc_upgrade(
                        from_sql_preset=column.sql_preset,
                        to_sql_preset=desired_column.sql_preset,
                    ):
                        alter_type_operations.append(
                            AlterColumnTypeOperation(
                                schema_name=schema_name,
                                table_name=actual_table.name,
                                column_name=column.name,
                                from_sql_preset=column.sql_preset,
                                to_sql_preset=desired_column.sql_preset,
                            )
                        )
                    else:
                        raise UnsupportedSchemaChangeError(
                            "Unsupported retained column change "
                            f"for '{actual_table.name}.{column.name}'."
                        )
                if desired_column.is_nullable != column.is_nullable:
                    if desired_column.is_nullable and not column.is_nullable:
                        alter_nullable_operations.append(
                            AlterColumnNullableOperation(
                                schema_name=schema_name,
                                table_name=actual_table.name,
                                column_name=column.name,
                                is_nullable=True,
                            )
                        )
                    else:
                        raise UnsupportedSchemaChangeError(
                            "Unsupported retained column nullability change "
                            f"for '{actual_table.name}.{column.name}'."
                        )
                if desired_column.default_value != column.default_value:
                    alter_default_operations.append(
                        AlterColumnDefaultOperation(
                            schema_name=schema_name,
                            table_name=actual_table.name,
                            column_name=column.name,
                            default_value=desired_column.default_value,
                        )
                    )

        for actual_table in sorted(actual_schema.tables, key=lambda item: item.name):
            if actual_table.name not in desired_tables:
                should_remove = preserved.removes_table(actual_table.name)
                if not should_remove and (
                    self._is_custom_table(actual_table.name)
                    or preserved.has_table(actual_table.name)
                ):
                    continue
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
                if (
                    actual_table is not None
                    and not column.is_nullable
                    and column.default_value is None
                ):
                    raise UnsupportedSchemaChangeError(
                        "Adding required column without default is unsafe "
                        f"for existing table '{desired_table.name}.{column.name}'."
                    )
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
            if desired_table.primary_key is None:
                continue
            actual_primary_key = (
                None if actual_table is None else actual_table.primary_key
            )
            if actual_primary_key == desired_table.primary_key:
                continue
            if actual_primary_key is not None:
                continue
            plan.add(
                AddPrimaryKeyOperation(
                    schema_name=schema_name,
                    table_name=desired_table.name,
                    constraint_name=desired_table.primary_key.name,
                    columns=desired_table.primary_key.columns,
                )
            )

        for operation in alter_type_operations:
            plan.add(operation)

        for operation in alter_nullable_operations:
            plan.add(operation)

        for operation in alter_default_operations:
            plan.add(operation)

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
        seed: SchemaSeed | ValidatedSchemaSpec,
        schema_name: str,
    ) -> PhysicalSchemaSnapshot:
        """Преобразует raw seed или валидированную spec в желаемый snapshot схемы."""
        if isinstance(seed, ValidatedSchemaSpec):
            return self._build_desired_schema_from_spec(
                schema_spec=seed,
                schema_name=schema_name,
            )
        return self._build_desired_schema_from_seed(seed=seed, schema_name=schema_name)

    def _build_desired_schema_from_seed(
        self,
        *,
        seed: SchemaSeed,
        schema_name: str,
    ) -> PhysicalSchemaSnapshot:
        """Строит желаемый snapshot напрямую из raw seed."""
        tables: list[TableSnapshot] = []
        for object_seed in seed.objects:
            tables.append(
                self._build_table_snapshot_from_seed(seed=seed, object_seed=object_seed)
            )
        return PhysicalSchemaSnapshot(schema_name=schema_name, tables=tuple(tables))

    def _build_desired_schema_from_spec(
        self,
        *,
        schema_spec: ValidatedSchemaSpec,
        schema_name: str,
    ) -> PhysicalSchemaSnapshot:
        """Строит желаемый snapshot из нормализованной и валидированной spec."""
        tables: list[TableSnapshot] = []
        for object_spec in schema_spec.objects:
            tables.append(
                self._build_table_snapshot_from_spec(
                    schema_spec=schema_spec,
                    object_spec=object_spec,
                )
            )
        tables.extend(self._build_many_to_many_table_snapshots(schema_spec=schema_spec))
        return PhysicalSchemaSnapshot(schema_name=schema_name, tables=tuple(tables))

    def _build_table_snapshot_from_seed(
        self,
        *,
        seed: SchemaSeed,
        object_seed: ObjectSeed,
    ) -> TableSnapshot:
        """Преобразует один object seed в snapshot таблицы с колонками и связями."""
        columns = tuple(
            self._build_column_snapshot_from_seed(field_seed)
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
        if object_seed.relations:
            raise UnsupportedSchemaChangeError(
                "Relations require normalized schema spec."
            )
        return TableSnapshot(
            name=object_seed.plural_name,
            columns=columns,
            primary_key=self._build_primary_key_snapshot(
                table_name=object_seed.plural_name,
                columns=columns,
            ),
            indexes=indexes,
            foreign_keys=(),
        )

    def _build_table_snapshot_from_spec(
        self,
        *,
        schema_spec: ValidatedSchemaSpec,
        object_spec: ValidatedObjectSpec,
    ) -> TableSnapshot:
        """Преобразует валидированный object spec в snapshot таблицы."""
        columns = tuple(
            self._build_column_snapshot_from_spec(field_spec)
            for field_spec in object_spec.fields
        )
        indexes = tuple(
            IndexSnapshot(
                name=index_spec.name,
                columns=index_spec.fields,
                is_unique=index_spec.is_unique,
            )
            for index_spec in object_spec.indexes
        )
        foreign_keys: list[ForeignKeySnapshot] = []
        for relation_spec in self._fk_relations_for_table(
            schema_spec=schema_spec,
            object_spec=object_spec,
        ):
            foreign_keys.append(
                self._build_foreign_key_snapshot_from_spec(
                    schema_spec=schema_spec,
                    relation_spec=relation_spec,
                )
            )
        return TableSnapshot(
            name=object_spec.plural_name,
            columns=columns,
            primary_key=self._build_primary_key_snapshot(
                table_name=object_spec.plural_name,
                columns=columns,
            ),
            indexes=indexes,
            foreign_keys=tuple(foreign_keys),
        )

    def _build_column_snapshot_from_seed(self, field_seed: FieldSeed) -> ColumnSnapshot:
        """Преобразует field seed в канонический snapshot PostgreSQL-колонки."""
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

    def _build_column_snapshot_from_spec(
        self,
        field_spec: ValidatedFieldSpec,
    ) -> ColumnSnapshot:
        """Преобразует валидированный field spec в snapshot PostgreSQL-колонки."""
        sql_preset = self._postgres_field_canonicalizer.sql_preset_from_field_type(
            field_spec.field_type
        )
        return ColumnSnapshot(
            name=field_spec.name,
            sql_preset=sql_preset,
            is_nullable=field_spec.is_nullable,
            default_value=self._postgres_field_canonicalizer.normalize_seed_default(
                raw_default=field_spec.default,
                sql_preset=sql_preset,
            ),
        )

    def _build_foreign_key_snapshot_from_spec(
        self,
        *,
        schema_spec: ValidatedSchemaSpec,
        relation_spec: ValidatedRelationSpec,
    ) -> ForeignKeySnapshot:
        """Строит snapshot foreign key из валидированной relation spec."""
        if not relation_spec.relation_type.is_fk_based():
            raise UnsupportedSchemaChangeError(
                "many_to_many relation does not have object FK snapshot."
            )
        if (
            relation_spec.foreign_key_name is None
            or relation_spec.fk_field is None
            or relation_spec.referenced_object is None
            or relation_spec.referenced_field is None
        ):
            raise UnsupportedSchemaChangeError("Incomplete FK relation spec.")
        referenced_object = schema_spec.get_object(relation_spec.referenced_object)
        if referenced_object is None:
            raise UnsupportedSchemaChangeError(
                f"Referenced object '{relation_spec.referenced_object}' not found."
            )
        return ForeignKeySnapshot(
            name=relation_spec.foreign_key_name,
            source_columns=(relation_spec.fk_field,),
            target_table_name=referenced_object.plural_name,
            target_columns=(relation_spec.referenced_field,),
            on_delete=self._normalize_on_delete(relation_spec.on_delete),
        )

    def _build_many_to_many_table_snapshots(
        self,
        *,
        schema_spec: ValidatedSchemaSpec,
    ) -> list[TableSnapshot]:
        """Строит snapshots физических join-таблиц для many_to_many relations."""
        tables: list[TableSnapshot] = []
        for relation_spec in self._iter_relation_specs(schema_spec):
            if relation_spec.relation_type != RelationTypeEnum.MANY_TO_MANY:
                continue
            if (
                relation_spec.relation_table_name is None
                or relation_spec.source_join_column_name is None
                or relation_spec.target_join_column_name is None
            ):
                raise UnsupportedSchemaChangeError(
                    "Incomplete many_to_many relation spec."
                )
            source_object = schema_spec.get_object(relation_spec.source_object)
            target_object = schema_spec.get_object(relation_spec.target_object)
            if source_object is None or target_object is None:
                raise UnsupportedSchemaChangeError(
                    "many_to_many relation references unknown object."
                )
            table_name = relation_spec.relation_table_name
            source_column = relation_spec.source_join_column_name
            target_column = relation_spec.target_join_column_name
            tables.append(
                TableSnapshot(
                    name=table_name,
                    columns=(
                        ColumnSnapshot(
                            name="id",
                            sql_preset=SqlTypePresetEnum.UUID,
                            is_nullable=False,
                            default_value="gen_random_uuid()",
                        ),
                        ColumnSnapshot(
                            name="created_at",
                            sql_preset=SqlTypePresetEnum.TIMESTAMPTZ,
                            is_nullable=False,
                            default_value="CURRENT_TIMESTAMP",
                        ),
                        ColumnSnapshot(
                            name=source_column,
                            sql_preset=SqlTypePresetEnum.UUID,
                            is_nullable=False,
                            default_value=None,
                        ),
                        ColumnSnapshot(
                            name=target_column,
                            sql_preset=SqlTypePresetEnum.UUID,
                            is_nullable=False,
                            default_value=None,
                        ),
                    ),
                    primary_key=PrimaryKeySnapshot(
                        name=SchemaNamingStrategy.primary_key_name(
                            table_name=table_name,
                        ),
                        columns=("id",),
                    ),
                    indexes=(
                        IndexSnapshot(
                            name=SchemaNamingStrategy.many_to_many_unique_index_name(
                                table_name=table_name,
                                source_column_name=source_column,
                                target_column_name=target_column,
                            ),
                            columns=(source_column, target_column),
                            is_unique=True,
                        ),
                        IndexSnapshot(
                            name=SchemaNamingStrategy.foreign_key_index_name(
                                table_name=table_name,
                                column_name=source_column,
                            ),
                            columns=(source_column,),
                            is_unique=False,
                        ),
                        IndexSnapshot(
                            name=SchemaNamingStrategy.foreign_key_index_name(
                                table_name=table_name,
                                column_name=target_column,
                            ),
                            columns=(target_column,),
                            is_unique=False,
                        ),
                    ),
                    foreign_keys=(
                        ForeignKeySnapshot(
                            name=SchemaNamingStrategy.foreign_key_name(
                                source_table_name=table_name,
                                source_column_name=source_column,
                                target_table_name=source_object.plural_name,
                            ),
                            source_columns=(source_column,),
                            target_table_name=source_object.plural_name,
                            target_columns=("id",),
                            on_delete=self._normalize_on_delete(
                                relation_spec.on_delete
                            ),
                        ),
                        ForeignKeySnapshot(
                            name=SchemaNamingStrategy.foreign_key_name(
                                source_table_name=table_name,
                                source_column_name=target_column,
                                target_table_name=target_object.plural_name,
                            ),
                            source_columns=(target_column,),
                            target_table_name=target_object.plural_name,
                            target_columns=("id",),
                            on_delete=self._normalize_on_delete(
                                relation_spec.on_delete
                            ),
                        ),
                    ),
                )
            )
        return tables

    @staticmethod
    def _build_primary_key_snapshot(
        *,
        table_name: str,
        columns: tuple[ColumnSnapshot, ...],
    ) -> PrimaryKeySnapshot | None:
        """Создает PK snapshot по id-колонке, если она есть в таблице."""
        for column in columns:
            if column.name == "id":
                return PrimaryKeySnapshot(
                    name=SchemaNamingStrategy.primary_key_name(table_name=table_name),
                    columns=("id",),
                )
        return None

    def _fk_relations_for_table(
        self,
        *,
        schema_spec: ValidatedSchemaSpec,
        object_spec: ValidatedObjectSpec,
    ) -> tuple[ValidatedRelationSpec, ...]:
        """Возвращает FK-based relations, физически принадлежащие таблице object."""
        return tuple(
            relation_spec
            for relation_spec in self._iter_relation_specs(schema_spec)
            if relation_spec.relation_type.is_fk_based()
            and relation_spec.owning_object == object_spec.singular_name
        )

    @staticmethod
    def _iter_relation_specs(
        schema_spec: ValidatedSchemaSpec,
    ) -> tuple[ValidatedRelationSpec, ...]:
        """Возвращает плоский список relation specs всей схемы."""
        return tuple(
            relation_spec
            for object_spec in schema_spec.objects
            for relation_spec in object_spec.relations
        )

    @staticmethod
    def _is_custom_table(table_name: str) -> bool:
        """Проверяет, принадлежит ли физическая таблица custom object namespace."""
        return has_custom_object_prefix(table_name)

    @staticmethod
    def _is_supported_timestamp_utc_upgrade(
        *,
        from_sql_preset: SqlTypePresetEnum,
        to_sql_preset: SqlTypePresetEnum,
    ) -> bool:
        return (
            from_sql_preset == SqlTypePresetEnum.TIMESTAMP
            and to_sql_preset == SqlTypePresetEnum.TIMESTAMPTZ
        )

    @staticmethod
    def _normalize_on_delete(value: str) -> str:
        """Приводит on_delete к каноническому lowercase-значению для snapshot."""
        mapping = {
            "restrict": "restrict",
            "cascade": "cascade",
            "set null": "set_null",
            "set_null": "set_null",
            "no action": "no_action",
            "no_action": "no_action",
        }
        try:
            return mapping[value.strip().lower()]
        except KeyError as exc:
            raise UnsupportedSchemaChangeError(
                f"Unsupported relation on_delete '{value}'."
            ) from exc

    @staticmethod
    def _normalize_relation_type(raw_type: str | RelationTypeEnum) -> RelationTypeEnum:
        """Валидирует тип связи."""
        normalized = str(
            raw_type.value if isinstance(raw_type, RelationTypeEnum) else raw_type
        )
        normalized = normalized.strip().lower()
        try:
            relation_type = RelationTypeEnum(normalized)
        except ValueError as exc:
            raise UnsupportedSchemaChangeError(
                f"Unsupported relation_type '{raw_type}'."
            ) from exc
        return relation_type
