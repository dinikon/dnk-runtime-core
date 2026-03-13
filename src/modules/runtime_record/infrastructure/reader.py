from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_record.application.contracts import (
    FindRuntimeRecordQuery,
    GetRuntimeRecordQuery,
    RuntimeRecordPayload,
    UpsertRuntimeRecordCommand,
)
from src.modules.runtime_record.application.ports.storage import (
    RuntimeRecordStoragePort,
)
from src.modules.runtime_record.domain.errors import (
    RuntimeRecordDataSourceNotFoundError,
    RuntimeRecordFieldNotFoundError,
    RuntimeRecordObjectNotFoundError,
)
from src.modules.runtime_schema.domain.field.configuration import RelationFieldSettings
from src.modules.runtime_schema.domain.field.entity import FieldMetadataEntity
from src.modules.runtime_schema.domain.field.value_object import FieldTypeVO
from src.modules.runtime_schema.domain.object.entity import ObjectMetadataEntity
from src.modules.runtime_schema.domain.source.value_object import DataSourceIdVO
from src.modules.runtime_schema.infrastructure.field_layout_compiler import (
    FieldLayoutCompiler,
)
from src.modules.runtime_schema.infrastructure.repositories import (
    SqlAlchemyFieldMetadataRepository,
    SqlAlchemyObjectMetadataRepository,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.errors import ValidationError
from src.modules.tenancy.infrastructure.persistence.data_source import (
    TenantDataSourceModel,
)


@dataclass(frozen=True, slots=True)
class _FieldMapping:
    field: FieldMetadataEntity
    columns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _ResolvedRuntimeObject:
    tenant_id: UUID
    object_entity: ObjectMetadataEntity
    data_source_model: TenantDataSourceModel
    field_mappings: tuple[_FieldMapping, ...]


class SqlAlchemyRuntimeRecordReader(RuntimeRecordStoragePort):
    def __init__(self, session: AsyncSession):
        self._session = session
        self._object_repository = SqlAlchemyObjectMetadataRepository(session)
        self._field_repository = SqlAlchemyFieldMetadataRepository(session)
        self._layout_compiler = FieldLayoutCompiler()

    async def get_record(
        self,
        query: GetRuntimeRecordQuery,
    ) -> RuntimeRecordPayload | None:
        resolved = await self._resolve_runtime_object(
            tenant_id=query.tenant_id,
            object_name_singular=query.object_name_singular,
        )
        row = await self._select_single_row(
            resolved=resolved,
            where_values={"id": query.record_id},
        )
        if row is None:
            return None
        return self._build_payload(
            resolved=resolved,
            row=row,
        )

    async def get_record_by_fields(
        self,
        query: FindRuntimeRecordQuery,
    ) -> RuntimeRecordPayload | None:
        resolved = await self._resolve_runtime_object(
            tenant_id=query.tenant_id,
            object_name_singular=query.object_name_singular,
        )
        where_values = self._serialize_filter_values(
            object_name_singular=resolved.object_entity.object_name.name_singular,
            field_mappings=resolved.field_mappings,
            filters=query.filters,
        )
        row = await self._select_single_row(
            resolved=resolved,
            where_values=where_values,
        )
        if row is None:
            return None
        return self._build_payload(
            resolved=resolved,
            row=row,
        )

    async def upsert_record(
        self,
        command: UpsertRuntimeRecordCommand,
    ) -> None:
        resolved = await self._resolve_runtime_object(
            tenant_id=command.tenant_id,
            object_name_singular=command.object_name_singular,
        )
        serialized_values = self._serialize_upsert_values(
            object_name_singular=resolved.object_entity.object_name.name_singular,
            field_mappings=resolved.field_mappings,
            values=command.values,
        )
        row_values: dict[str, object] = {"id": command.record_id}
        row_values.update(serialized_values)

        now = datetime.now(UTC)
        if "created_at" not in row_values:
            row_values["created_at"] = now
        if "updated_at" not in row_values:
            row_values["updated_at"] = now

        ordered_columns = sorted(row_values)
        table_reference = self._qualified_table(
            schema=resolved.data_source_model.schema,
            table_name=resolved.object_entity.object_name.name_plural,
        )
        columns_sql = ", ".join(
            self._quote_identifier(column_name) for column_name in ordered_columns
        )
        values_sql = ", ".join(f":{column_name}" for column_name in ordered_columns)

        update_columns = [
            column_name
            for column_name in ordered_columns
            if column_name not in {"id", "created_at"}
        ]
        if update_columns:
            updates_sql = ", ".join(
                (
                    f"{self._quote_identifier(column_name)} = "
                    f"excluded.{self._quote_identifier(column_name)}"
                )
                for column_name in update_columns
            )
            sql = (
                f"INSERT INTO {table_reference} ({columns_sql}) "
                f"VALUES ({values_sql}) "
                f"ON CONFLICT ({self._quote_identifier('id')}) "
                f"DO UPDATE SET {updates_sql}"
            )
        else:
            sql = (
                f"INSERT INTO {table_reference} ({columns_sql}) "
                f"VALUES ({values_sql}) "
                f"ON CONFLICT ({self._quote_identifier('id')}) DO NOTHING"
            )

        parameters = {
            column_name: self._bind_sql_value(row_values[column_name])
            for column_name in ordered_columns
        }
        await self._session.execute(text(sql), parameters)
        await self._session.flush()

    async def _resolve_runtime_object(
        self,
        *,
        tenant_id: UUID,
        object_name_singular: str,
    ) -> _ResolvedRuntimeObject:
        normalized_object_name = object_name_singular.strip().lower()
        data_source_model = await self._session.scalar(
            select(TenantDataSourceModel)
            .where(TenantDataSourceModel.tenant_id == str(tenant_id))
            .limit(1)
        )
        if data_source_model is None:
            raise RuntimeRecordDataSourceNotFoundError(str(tenant_id))

        object_entity = await self._object_repository.get_by_name(
            tenant_id=EntityIdVO.from_value(tenant_id),
            data_source_id=DataSourceIdVO.from_value(data_source_model.id),
            object_name_singular=normalized_object_name,
        )
        if object_entity is None or not object_entity.is_active:
            raise RuntimeRecordObjectNotFoundError(normalized_object_name)

        fields = await self._field_repository.list_by_object(object_id=object_entity.id)
        active_fields = [field for field in fields if field.is_active]
        field_mappings = tuple(self._build_field_mappings(fields=active_fields))
        return _ResolvedRuntimeObject(
            tenant_id=tenant_id,
            object_entity=object_entity,
            data_source_model=data_source_model,
            field_mappings=field_mappings,
        )

    async def _select_single_row(
        self,
        *,
        resolved: _ResolvedRuntimeObject,
        where_values: dict[str, object],
    ):
        if not where_values:
            raise ValidationError("where_values must not be empty")

        selected_columns = {"id"}
        for mapping in resolved.field_mappings:
            selected_columns.update(mapping.columns)

        table_reference = self._qualified_table(
            schema=resolved.data_source_model.schema,
            table_name=resolved.object_entity.object_name.name_plural,
        )
        columns_sql = ", ".join(
            self._quote_identifier(column_name)
            for column_name in sorted(selected_columns)
        )

        where_clauses: list[str] = []
        parameters: dict[str, object] = {}
        for index, (column_name, column_value) in enumerate(sorted(where_values.items())):
            quoted_column = self._quote_identifier(column_name)
            if column_value is None:
                where_clauses.append(f"{quoted_column} IS NULL")
                continue
            parameter_name = f"p_{index}"
            where_clauses.append(f"{quoted_column} = :{parameter_name}")
            parameters[parameter_name] = self._bind_sql_value(column_value)

        where_sql = " AND ".join(where_clauses)
        sql = (
            f"SELECT {columns_sql} "
            f"FROM {table_reference} "
            f"WHERE {where_sql} "
            "LIMIT 1"
        )
        result = await self._session.execute(text(sql), parameters)
        return result.mappings().first()

    def _build_payload(
        self,
        *,
        resolved: _ResolvedRuntimeObject,
        row,
    ) -> RuntimeRecordPayload:
        system_values: dict[str, object] = {}
        custom_values: dict[str, object] = {}
        for mapping in resolved.field_mappings:
            value = self._deserialize_field_value(mapping=mapping, row=row)
            if mapping.field.is_custom:
                custom_values[mapping.field.field_name.value] = value
            else:
                system_values[mapping.field.field_name.value] = value

        raw_record_id = row["id"]
        parsed_record_id = (
            raw_record_id if isinstance(raw_record_id, UUID) else UUID(str(raw_record_id))
        )
        return RuntimeRecordPayload(
            tenant_id=resolved.tenant_id,
            object_name_singular=resolved.object_entity.object_name.name_singular,
            record_id=parsed_record_id,
            system_values=system_values,
            custom_values=custom_values,
        )

    def _build_field_mappings(
        self,
        *,
        fields: list[FieldMetadataEntity],
    ) -> list[_FieldMapping]:
        mappings: list[_FieldMapping] = []
        for field in fields:
            compiled = self._layout_compiler._compile_field_columns(field)  # noqa: SLF001
            if compiled.is_virtual:
                continue
            columns = tuple(column.name for column in compiled.columns)
            if not columns:
                continue
            mappings.append(
                _FieldMapping(
                    field=field,
                    columns=columns,
                )
            )
        return mappings

    def _serialize_filter_values(
        self,
        *,
        object_name_singular: str,
        field_mappings: tuple[_FieldMapping, ...],
        filters: dict[str, object],
    ) -> dict[str, object]:
        if not filters:
            raise ValidationError("filters must not be empty")
        return self._serialize_field_payload(
            object_name_singular=object_name_singular,
            field_mappings=field_mappings,
            payload=filters,
        )

    def _serialize_upsert_values(
        self,
        *,
        object_name_singular: str,
        field_mappings: tuple[_FieldMapping, ...],
        values: dict[str, object],
    ) -> dict[str, object]:
        return self._serialize_field_payload(
            object_name_singular=object_name_singular,
            field_mappings=field_mappings,
            payload=values,
        )

    def _serialize_field_payload(
        self,
        *,
        object_name_singular: str,
        field_mappings: tuple[_FieldMapping, ...],
        payload: dict[str, object],
    ) -> dict[str, object]:
        mapping_by_field_name = {
            mapping.field.field_name.value: mapping for mapping in field_mappings
        }
        serialized: dict[str, object] = {}
        for raw_field_name, raw_value in payload.items():
            normalized_field_name = raw_field_name.strip().lower()
            mapping = mapping_by_field_name.get(normalized_field_name)
            if mapping is None:
                raise RuntimeRecordFieldNotFoundError(
                    object_name_singular=object_name_singular,
                    field_name=normalized_field_name,
                )
            field_payload = self._serialize_field_value(
                mapping=mapping,
                value=raw_value,
            )
            for column_name, column_value in field_payload.items():
                if (
                    column_name in serialized
                    and serialized[column_name] != column_value
                ):
                    raise ValidationError(
                        f"conflicting values for column '{column_name}'"
                    )
                serialized[column_name] = column_value
        return serialized

    @staticmethod
    def _deserialize_field_value(
        *,
        mapping: _FieldMapping,
        row,
    ) -> object:
        field = mapping.field
        if len(mapping.columns) == 1:
            return row[mapping.columns[0]]

        if field.field_type == FieldTypeVO.FULL_NAME:
            payload = {
                "last_name": row.get(f"{field.field_name.value}_last_name"),
                "middle_name": row.get(f"{field.field_name.value}_middle_name"),
                "first_name": row.get(f"{field.field_name.value}_first_name"),
            }
            if all(value is None for value in payload.values()):
                return None
            return payload

        if field.field_type == FieldTypeVO.ADDRESS:
            payload = {
                "country": row.get(f"{field.field_name.value}_country"),
                "region": row.get(f"{field.field_name.value}_region"),
                "city": row.get(f"{field.field_name.value}_city"),
                "address_line": row.get(f"{field.field_name.value}_address_line"),
                "post_code": row.get(f"{field.field_name.value}_post_code"),
            }
            if all(value is None for value in payload.values()):
                return None
            return payload

        if field.field_type == FieldTypeVO.CURRENCY:
            payload = {
                "amount_minor": row.get(f"{field.field_name.value}_amount_minor"),
                "currency": row.get(f"{field.field_name.value}_currency"),
            }
            if all(value is None for value in payload.values()):
                return None
            return payload

        payload: dict[str, object] = {}
        for column_name in mapping.columns:
            normalized_key = column_name
            field_prefix = f"{field.field_name.value}_"
            if column_name.startswith(field_prefix):
                normalized_key = column_name[len(field_prefix):]
            payload[normalized_key] = row.get(column_name)
        if all(value is None for value in payload.values()):
            return None
        return payload

    @staticmethod
    def _serialize_field_value(
        *,
        mapping: _FieldMapping,
        value: object,
    ) -> dict[str, object]:
        field = mapping.field
        field_name = field.field_name.value
        if len(mapping.columns) == 1:
            return {mapping.columns[0]: value}

        if value is None:
            return {column_name: None for column_name in mapping.columns}

        if not isinstance(value, dict):
            raise ValidationError(
                f"field '{field_name}' expects object payload for type '{field.field_type.value}'"
            )

        if field.field_type == FieldTypeVO.FULL_NAME:
            return {
                f"{field_name}_last_name": value.get("last_name"),
                f"{field_name}_middle_name": value.get("middle_name"),
                f"{field_name}_first_name": value.get("first_name"),
            }

        if field.field_type == FieldTypeVO.ADDRESS:
            return {
                f"{field_name}_country": value.get("country"),
                f"{field_name}_region": value.get("region"),
                f"{field_name}_city": value.get("city"),
                f"{field_name}_address_line": value.get("address_line"),
                f"{field_name}_post_code": value.get("post_code"),
            }

        if field.field_type == FieldTypeVO.CURRENCY:
            return {
                f"{field_name}_amount_minor": value.get("amount_minor"),
                f"{field_name}_currency": value.get("currency"),
            }

        relation_settings = (
            field.settings
            if isinstance(field.settings, RelationFieldSettings)
            else RelationFieldSettings()
        )
        if (
            field.field_type == FieldTypeVO.RELATION
            and relation_settings.max_links != 1
        ):
            raise ValidationError(
                f"field '{field_name}' is virtual relation and cannot be persisted directly"
            )

        payload: dict[str, object] = {}
        field_prefix = f"{field_name}_"
        for column_name in mapping.columns:
            key = (
                column_name[len(field_prefix):]
                if column_name.startswith(field_prefix)
                else column_name
            )
            payload[column_name] = value.get(column_name, value.get(key))
        return payload

    def _qualified_table(self, *, schema: str, table_name: str) -> str:
        dialect_name = self._session.get_bind().dialect.name.lower()
        if dialect_name == "postgresql":
            return (
                f"{self._quote_identifier(schema)}."
                f"{self._quote_identifier(table_name)}"
            )
        physical_table = f"{schema}__{table_name}"
        return self._quote_identifier(physical_table)

    @staticmethod
    def _quote_identifier(value: str) -> str:
        return '"' + value.replace('"', '""') + '"'

    @staticmethod
    def _bind_sql_value(value: object) -> object:
        if isinstance(value, UUID):
            return str(value)
        return value


__all__ = ["SqlAlchemyRuntimeRecordReader"]
