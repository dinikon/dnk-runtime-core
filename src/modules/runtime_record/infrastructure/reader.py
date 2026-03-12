from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_record.application.contracts import (
    GetRuntimeRecordQuery,
    RuntimeRecordPayload,
)
from src.modules.runtime_record.application.ports.storage import (
    RuntimeRecordReaderPort,
)
from src.modules.runtime_record.domain.errors import (
    RuntimeRecordDataSourceNotFoundError,
    RuntimeRecordObjectNotFoundError,
)
from src.modules.runtime_schema.domain.field.entity import FieldMetadataEntity
from src.modules.runtime_schema.domain.field.value_object import FieldTypeVO
from src.modules.runtime_schema.domain.source.value_object import DataSourceIdVO
from src.modules.runtime_schema.infrastructure.field_layout_compiler import (
    FieldLayoutCompiler,
)
from src.modules.runtime_schema.infrastructure.repositories import (
    SqlAlchemyFieldMetadataRepository,
    SqlAlchemyObjectMetadataRepository,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.infrastructure.persistence.data_source import (
    TenantDataSourceModel,
)


@dataclass(frozen=True, slots=True)
class _FieldMapping:
    field: FieldMetadataEntity
    columns: tuple[str, ...]


class SqlAlchemyRuntimeRecordReader(RuntimeRecordReaderPort):
    def __init__(self, session: AsyncSession):
        self._session = session
        self._object_repository = SqlAlchemyObjectMetadataRepository(session)
        self._field_repository = SqlAlchemyFieldMetadataRepository(session)
        self._layout_compiler = FieldLayoutCompiler()

    async def get_record(
        self,
        query: GetRuntimeRecordQuery,
    ) -> RuntimeRecordPayload | None:
        tenant_id = query.tenant_id
        record_id = query.record_id
        normalized_object_name = query.object_name_singular.strip().lower()
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
        field_mappings = self._build_field_mappings(fields=active_fields)

        selected_columns = {"id"}
        for mapping in field_mappings:
            selected_columns.update(mapping.columns)

        table_reference = self._qualified_table(
            schema=data_source_model.schema,
            table_name=object_entity.object_name.name_plural,
        )
        columns_sql = ", ".join(
            self._quote_identifier(column_name)
            for column_name in sorted(selected_columns)
        )
        sql = (
            f"SELECT {columns_sql} "
            f"FROM {table_reference} "
            f"WHERE {self._quote_identifier('id')} = :record_id "
            "LIMIT 1"
        )
        result = await self._session.execute(
            text(sql),
            {"record_id": str(record_id)},
        )
        row = result.mappings().first()
        if row is None:
            return None

        system_values: dict[str, object] = {}
        custom_values: dict[str, object] = {}
        for mapping in field_mappings:
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
            tenant_id=tenant_id,
            object_name_singular=object_entity.object_name.name_singular,
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


__all__ = ["SqlAlchemyRuntimeRecordReader"]
