from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.ports.schema_manager import (
    TenantSchemaManagerProtocol,
)
from src.modules.runtime_schema.application.relations.ports.schema_manager import (
    RelationSchemaManagerProtocol,
)
from src.modules.runtime_schema.domain.entities import (
    FieldMetadata,
    ObjectMetadata,
    RelationMetadata,
    SystemFieldDefinition,
    SystemObjectDefinition,
)
from src.modules.runtime_schema.domain.value_objects.field_type import (
    RuntimeSchemaFieldType,
)
from src.modules.runtime_schema.domain.value_objects.relation_kind import (
    RuntimeSchemaRelationKind,
)
from src.modules.runtime_schema.domain.value_objects.relation_on_delete import (
    RuntimeSchemaRelationOnDelete,
)


class SqlAlchemyTenantSchemaManager(
    TenantSchemaManagerProtocol,
    RelationSchemaManagerProtocol,
):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def ensure_system_object(
        self,
        *,
        schema: str,
        object_definition: SystemObjectDefinition,
    ) -> None:
        bind = self._session.get_bind()
        if bind.dialect.name != "postgresql":
            return

        qualified_table_name = self._quote_schema_table(
            schema, object_definition.table_name
        )
        create_columns_sql = ", ".join(
            self._build_create_column_sql(field_definition)
            for field_definition in object_definition.fields
        )
        await self._session.execute(
            text(
                f"CREATE TABLE IF NOT EXISTS {qualified_table_name} "
                f"({create_columns_sql})"
            )
        )

        for field_definition in object_definition.fields:
            if field_definition.is_primary_key:
                continue
            await self._session.execute(
                text(
                    f"ALTER TABLE {qualified_table_name} "
                    f"ADD COLUMN IF NOT EXISTS "
                    f"{self._build_add_column_sql(field_definition)}"
                )
            )

    async def ensure_relation(
        self,
        *,
        schema: str,
        relation: RelationMetadata,
        source_object: ObjectMetadata,
        source_field: FieldMetadata | None,
        target_object: ObjectMetadata,
        target_field: FieldMetadata | None,
    ) -> None:
        bind = self._session.get_bind()
        if bind.dialect.name != "postgresql":
            return

        if relation.kind == RuntimeSchemaRelationKind.MANY_TO_MANY:
            await self._ensure_many_to_many_relation(
                schema=schema,
                relation=relation,
                source_object=source_object,
                target_object=target_object,
            )
            return

        if source_field is None or target_field is None:
            return

        await self._ensure_owner_relation(
            schema=schema,
            relation=relation,
            source_object=source_object,
            source_field=source_field,
            target_object=target_object,
            target_field=target_field,
        )

    async def drop_relation(
        self,
        *,
        schema: str,
        relation: RelationMetadata,
        source_object: ObjectMetadata,
        source_field: FieldMetadata | None,
        target_object: ObjectMetadata,
        target_field: FieldMetadata | None,
    ) -> None:
        bind = self._session.get_bind()
        if bind.dialect.name != "postgresql":
            return

        if relation.kind == RuntimeSchemaRelationKind.MANY_TO_MANY:
            if relation.junction_table_name is None:
                return
            await self._session.execute(
                text(
                    "DROP TABLE IF EXISTS "
                    f"{self._quote_schema_table(schema, relation.junction_table_name)}"
                )
            )
            return

        if source_field is None:
            return

        source_table = self._quote_schema_table(schema, source_object.table_name)
        await self._session.execute(
            text(
                f"ALTER TABLE {source_table} "
                f"DROP CONSTRAINT IF EXISTS {self._quote_identifier(self._fk_name(relation))}"
            )
        )
        await self._session.execute(
            text(
                "DROP INDEX IF EXISTS "
                f"{self._quote_schema_object(schema, self._owner_index_name(relation))}"
            )
        )

    def _quote_schema_table(self, schema: str, table_name: str) -> str:
        bind = self._session.get_bind()
        quote = bind.dialect.identifier_preparer.quote
        return f"{quote(schema)}.{quote(table_name)}"

    def _quote_schema_object(self, schema: str, object_name: str) -> str:
        bind = self._session.get_bind()
        quote = bind.dialect.identifier_preparer.quote
        return f"{quote(schema)}.{quote(object_name)}"

    def _build_create_column_sql(self, field_definition: SystemFieldDefinition) -> str:
        parts = [
            self._quote_identifier(field_definition.column_name),
            self._sql_type(field_definition.field_type),
        ]
        if field_definition.is_primary_key:
            parts.append("PRIMARY KEY")
        if not field_definition.is_nullable:
            parts.append("NOT NULL")
        default_sql = self._default_sql(field_definition)
        if default_sql is not None:
            parts.append(f"DEFAULT {default_sql}")
        if field_definition.is_unique and not field_definition.is_primary_key:
            parts.append("UNIQUE")
        return " ".join(parts)

    def _build_add_column_sql(self, field_definition: SystemFieldDefinition) -> str:
        parts = [
            self._quote_identifier(field_definition.column_name),
            self._sql_type(field_definition.field_type),
        ]
        if not field_definition.is_nullable:
            parts.append("NOT NULL")
        default_sql = self._default_sql(field_definition)
        if default_sql is not None:
            parts.append(f"DEFAULT {default_sql}")
        if field_definition.is_unique:
            parts.append("UNIQUE")
        return " ".join(parts)

    def _quote_identifier(self, value: str) -> str:
        bind = self._session.get_bind()
        return bind.dialect.identifier_preparer.quote(value)

    async def _ensure_owner_relation(
        self,
        *,
        schema: str,
        relation: RelationMetadata,
        source_object: ObjectMetadata,
        source_field: FieldMetadata,
        target_object: ObjectMetadata,
        target_field: FieldMetadata,
    ) -> None:
        source_table_name = source_object.table_name
        target_table_name = target_object.table_name
        source_table = self._quote_schema_table(schema, source_table_name)
        target_table = self._quote_schema_table(schema, target_table_name)
        fk_name = self._fk_name(relation)
        on_delete = self._sql_on_delete(relation.on_delete)
        source_column = self._quote_identifier(source_field.name_field)
        target_column = self._quote_identifier(target_field.name_field)

        await self._ensure_constraint(
            schema=schema,
            table_name=source_table_name,
            constraint_name=fk_name,
            ddl=(
                f"ALTER TABLE {source_table} "
                f"ADD CONSTRAINT {self._quote_identifier(fk_name)} "
                f"FOREIGN KEY ({source_column}) "
                f"REFERENCES {target_table} ({target_column}) "
                f"ON DELETE {on_delete}"
            ),
        )

        index_name = self._owner_index_name(relation)
        if relation.kind == RuntimeSchemaRelationKind.ONE_TO_ONE:
            await self._session.execute(
                text(
                    f"CREATE UNIQUE INDEX IF NOT EXISTS {self._quote_identifier(index_name)} "
                    f"ON {source_table} ({source_column})"
                )
            )
            return

        await self._session.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS {self._quote_identifier(index_name)} "
                f"ON {source_table} ({source_column})"
            )
        )

    async def _ensure_many_to_many_relation(
        self,
        *,
        schema: str,
        relation: RelationMetadata,
        source_object: ObjectMetadata,
        target_object: ObjectMetadata,
    ) -> None:
        if relation.junction_table_name is None:
            return

        junction_table = self._quote_schema_table(schema, relation.junction_table_name)
        source_column_name = self._junction_source_column_name(source_object)
        target_column_name = self._junction_target_column_name(target_object)
        source_column = self._quote_identifier(source_column_name)
        target_column = self._quote_identifier(target_column_name)
        source_table = self._quote_schema_table(schema, source_object.table_name)
        target_table = self._quote_schema_table(schema, target_object.table_name)
        source_fk_name = f"{self._fk_name(relation)}_src"
        target_fk_name = f"{self._fk_name(relation)}_tgt"

        await self._session.execute(
            text(
                f"CREATE TABLE IF NOT EXISTS {junction_table} ("
                f"{source_column} UUID NOT NULL, "
                f"{target_column} UUID NOT NULL, "
                '"created_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, '
                '"updated_at" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, '
                f"PRIMARY KEY ({source_column}, {target_column})"
                ")"
            )
        )
        await self._ensure_constraint(
            schema=schema,
            table_name=relation.junction_table_name,
            constraint_name=source_fk_name,
            ddl=(
                f"ALTER TABLE {junction_table} "
                f"ADD CONSTRAINT {self._quote_identifier(source_fk_name)} "
                f"FOREIGN KEY ({source_column}) "
                f'REFERENCES {source_table} ("id") ON DELETE CASCADE'
            ),
        )
        await self._ensure_constraint(
            schema=schema,
            table_name=relation.junction_table_name,
            constraint_name=target_fk_name,
            ddl=(
                f"ALTER TABLE {junction_table} "
                f"ADD CONSTRAINT {self._quote_identifier(target_fk_name)} "
                f"FOREIGN KEY ({target_column}) "
                f'REFERENCES {target_table} ("id") ON DELETE CASCADE'
            ),
        )
        await self._session.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS {self._quote_identifier(self._many_to_many_target_index_name(relation))} "
                f"ON {junction_table} ({target_column})"
            )
        )

    async def _ensure_constraint(
        self,
        *,
        schema: str,
        table_name: str,
        constraint_name: str,
        ddl: str,
    ) -> None:
        await self._session.execute(
            text(
                "DO $ddl$ "
                "BEGIN "
                "IF NOT EXISTS ("
                "SELECT 1 "
                "FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "JOIN pg_namespace n ON n.oid = t.relnamespace "
                f"WHERE c.conname = {self._sql_literal(constraint_name)} "
                f"AND n.nspname = {self._sql_literal(schema)} "
                f"AND t.relname = {self._sql_literal(table_name)}"
                ") THEN "
                f"{ddl}; "
                "END IF; "
                "END "
                "$ddl$;"
            )
        )

    @staticmethod
    def _fk_name(relation: RelationMetadata) -> str:
        return f"fk_rel_{relation.id.hex[:12]}"

    @classmethod
    def _owner_index_name(cls, relation: RelationMetadata) -> str:
        prefix = "uq" if relation.kind == RuntimeSchemaRelationKind.ONE_TO_ONE else "ix"
        return f"{prefix}_rel_{relation.id.hex[:12]}_src"

    @staticmethod
    def _many_to_many_target_index_name(relation: RelationMetadata) -> str:
        return f"ix_rel_{relation.id.hex[:12]}_tgt"

    @staticmethod
    def _junction_source_column_name(source_object: ObjectMetadata) -> str:
        return f"source_{source_object.name_singular}_id"

    @staticmethod
    def _junction_target_column_name(target_object: ObjectMetadata) -> str:
        return f"target_{target_object.name_singular}_id"

    @staticmethod
    def _sql_on_delete(value: RuntimeSchemaRelationOnDelete) -> str:
        mapping = {
            RuntimeSchemaRelationOnDelete.RESTRICT: "RESTRICT",
            RuntimeSchemaRelationOnDelete.SET_NULL: "SET NULL",
            RuntimeSchemaRelationOnDelete.CASCADE: "CASCADE",
        }
        return mapping[value]

    @staticmethod
    def _sql_literal(value: str) -> str:
        escaped = value.replace("'", "''")
        return f"'{escaped}'"

    @staticmethod
    def _sql_type(field_type: RuntimeSchemaFieldType) -> str:
        mapping = {
            RuntimeSchemaFieldType.UUID: "UUID",
            RuntimeSchemaFieldType.STRING: "VARCHAR(255)",
            RuntimeSchemaFieldType.LONG_TEXT: "TEXT",
            RuntimeSchemaFieldType.DATETIME: "TIMESTAMP WITH TIME ZONE",
            RuntimeSchemaFieldType.BOOLEAN: "BOOLEAN",
            RuntimeSchemaFieldType.INTEGER: "BIGINT",
            RuntimeSchemaFieldType.DECIMAL: "NUMERIC(18, 2)",
            RuntimeSchemaFieldType.JSON: "JSONB",
        }
        return mapping[field_type]

    @staticmethod
    def _default_sql(field_definition: SystemFieldDefinition) -> str | None:
        if field_definition.default_sql is not None:
            return field_definition.default_sql
        if field_definition.default_value is None:
            return None
        if isinstance(field_definition.default_value, bool):
            return "TRUE" if field_definition.default_value else "FALSE"
        if isinstance(field_definition.default_value, (int, float)):
            return str(field_definition.default_value)
        if isinstance(field_definition.default_value, str):
            escaped = field_definition.default_value.replace("'", "''")
            return f"'{escaped}'"
        return None
