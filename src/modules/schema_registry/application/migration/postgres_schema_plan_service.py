from __future__ import annotations

from src.modules.schema_registry.application.migration.operations import (
    AddColumnOperation,
    AlterColumnDefaultOperation,
    AlterColumnNullableOperation,
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
from src.modules.schema_registry.domain.object.naming import has_custom_object_prefix
from src.modules.schema_registry.domain.seed.field_seed import FieldSeed
from src.modules.schema_registry.domain.seed.object_seed import ObjectSeed
from src.modules.schema_registry.domain.seed.relation_seed import RelationSeed
from src.modules.schema_registry.domain.seed.relation_type import RelationTypeEnum
from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed
from src.modules.schema_registry.domain.seed.validated_schema_spec import (
    ValidatedFieldSpec,
    ValidatedObjectSpec,
    ValidatedRelationSpec,
    ValidatedSchemaSpec,
)


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
    ) -> MigrationPlan:
        """Строит diff-план между желаемой и фактической схемой PostgreSQL.

        Порядок операций важен: сначала снимаются FK и индексы, которые могут
        блокировать изменение таблиц, затем добавляются недостающие элементы.
        Небезопасные изменения retained-колонок явно отклоняются.
        """
        plan = MigrationPlan()
        desired_schema = self._build_desired_schema(seed=seed, schema_name=schema_name)
        actual_tables = {table.name: table for table in actual_schema.tables}
        desired_tables = {table.name: table for table in desired_schema.tables}
        alter_default_operations: list[AlterColumnDefaultOperation] = []
        alter_nullable_operations: list[AlterColumnNullableOperation] = []

        for actual_table in sorted(actual_schema.tables, key=lambda item: item.name):
            desired_table = desired_tables.get(actual_table.name)
            if desired_table is None and self._is_custom_table(actual_table.name):
                continue
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
            if desired_table is None and self._is_custom_table(actual_table.name):
                continue
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

                if desired_column.sql_preset != column.sql_preset:
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
                if self._is_custom_table(actual_table.name):
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
        foreign_keys: list[ForeignKeySnapshot] = []
        for relation_seed in object_seed.relations:
            relation_type = self._normalize_relation_type(relation_seed.relation_type)
            if relation_type == RelationTypeEnum.ONE_TO_ONE:
                raise UnsupportedSchemaChangeError(
                    "one_to_one relations require normalized schema spec."
                )
            target_object = seed.get_object(relation_seed.target_object)
            if target_object is None:
                raise UnsupportedSchemaChangeError(
                    f"Target object '{relation_seed.target_object}' not found in seed."
                )
            foreign_keys.append(
                self._build_foreign_key_snapshot(
                    relation_seed=relation_seed,
                    target_table_name=target_object.plural_name,
                )
            )
        return TableSnapshot(
            name=object_seed.plural_name,
            columns=columns,
            indexes=indexes,
            foreign_keys=tuple(foreign_keys),
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
        for relation_spec in object_spec.relations:
            target_object = schema_spec.get_object(relation_spec.target_object)
            if target_object is None:
                raise UnsupportedSchemaChangeError(
                    f"Target object '{relation_spec.target_object}' not found in seed."
                )
            foreign_keys.append(
                self._build_foreign_key_snapshot(
                    relation_seed=relation_spec,
                    target_table_name=target_object.plural_name,
                )
            )
        return TableSnapshot(
            name=object_spec.plural_name,
            columns=columns,
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

    def _build_foreign_key_snapshot(
        self,
        *,
        relation_seed: RelationSeed | ValidatedRelationSpec,
        target_table_name: str,
    ) -> ForeignKeySnapshot:
        """Строит snapshot foreign key из relation seed/spec и target-таблицы."""
        relation_type = self._normalize_relation_type(relation_seed.relation_type)
        if (
            relation_type == RelationTypeEnum.ONE_TO_ONE
            and isinstance(relation_seed, ValidatedRelationSpec)
            and relation_seed.unique_index_name is None
        ):
            raise UnsupportedSchemaChangeError(
                "one_to_one relations require normalized schema spec."
            )
        return ForeignKeySnapshot(
            name=relation_seed.name,
            source_columns=(relation_seed.source_field,),
            target_table_name=target_table_name,
            target_columns=(relation_seed.target_field,),
            on_delete=self._normalize_on_delete(relation_seed.on_delete),
        )

    @staticmethod
    def _is_custom_table(table_name: str) -> bool:
        """Проверяет, принадлежит ли физическая таблица custom object namespace."""
        return has_custom_object_prefix(table_name)

    @staticmethod
    def _normalize_on_delete(value: str) -> str:
        """Приводит on_delete к каноническому lowercase-значению для snapshot."""
        mapping = {
            "restrict": "restrict",
            "cascade": "cascade",
            "set null": "set null",
            "set_null": "set null",
            "no action": "no action",
            "no_action": "no action",
        }
        try:
            return mapping[value.strip().lower()]
        except KeyError as exc:
            raise UnsupportedSchemaChangeError(
                f"Unsupported relation on_delete '{value}'."
            ) from exc

    @staticmethod
    def _normalize_relation_type(raw_type: str | RelationTypeEnum) -> RelationTypeEnum:
        """Валидирует тип связи и оставляет только source-owned FK варианты MVP."""
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
        if not relation_type.is_source_owned_fk():
            raise UnsupportedSchemaChangeError(
                f"Unsupported relation_type '{relation_type.value}' for MVP."
            )
        return relation_type
