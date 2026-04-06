from src.modules.schema_registry.domain.migration.plan import MigrationPlan
from src.modules.schema_registry.domain.migration.operations import (
    CreateSchemaOperation,
    CreateTableOperation,
    DropTableOperation,
    AddColumnOperation,
    DropColumnOperation,
    CreateIndexOperation,
    AddForeignKeyOperation,
)
from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed


class SchemaDiffService:
    def build_create_plan(
        self,
        *,
        schema_name: str,
        seed: SchemaSeed,
    ) -> MigrationPlan:
        plan = MigrationPlan()
        plan.add(CreateSchemaOperation(schema_name=schema_name))

        for object_seed in seed.objects:
            plan.add(
                CreateTableOperation(
                    schema_name=schema_name,
                    table_name=object_seed.plural_name,
                )
            )

            for field in object_seed.fields:
                plan.add(
                    AddColumnOperation(
                        schema_name=schema_name,
                        table_name=object_seed.plural_name,
                        column_name=field.name,
                        column_type=self._map_seed_type_to_sql(field.type),
                        is_nullable=field.is_nullable,
                        default=field.default,
                    )
                )

            for index in object_seed.indexes:
                plan.add(
                    CreateIndexOperation(
                        schema_name=schema_name,
                        table_name=object_seed.plural_name,
                        index_name=index.name,
                        columns=index.fields,
                        is_unique=index.is_unique,
                    )
                )

            for relation in object_seed.relations:
                target_object = seed.get_object(relation.target_object)
                if target_object is None:
                    raise ValueError(
                        f"Target object '{relation.target_object}' not found in seed."
                    )

                plan.add(
                    AddForeignKeyOperation(
                        schema_name=schema_name,
                        table_name=object_seed.plural_name,
                        constraint_name=relation.name,
                        column_name=relation.source_field,
                        target_schema_name=schema_name,
                        target_table_name=target_object.plural_name,
                        target_column_name=relation.target_field,
                        on_delete=relation.on_delete,
                    )
                )

        return plan

    def build_diff_plan(
        self,
        *,
        schema_name: str,
        seed: SchemaSeed,
        actual_schema,
    ) -> MigrationPlan:
        plan = MigrationPlan()

        # 1. добавить отсутствующие таблицы
        # 2. добавить отсутствующие колонки
        # 3. удалить лишние foreign keys / indexes / columns / tables
        # 4. изменение type в MVP запрещать exception'ом

        return plan

    def _map_seed_type_to_sql(self, field_type: str) -> str:
        mapping = {
            "uuid": "uuid",
            "text": "text",
            "int": "integer",
            "decimal": "numeric(18,2)",
            "bool": "boolean",
            "datetime": "timestamp without time zone",
            "date": "date",
            "json": "jsonb",
            "select": "text",
            "multiselect": "jsonb",
        }
        try:
            return mapping[field_type]
        except KeyError:
            raise ValueError(f"Unsupported field type: {field_type}")
