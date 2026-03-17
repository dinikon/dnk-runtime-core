from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from src.modules.runtime_record.application.commands import WriteRuntimeValuesCommand
from src.modules.runtime_record.application.dto import RuntimeRecordValuesDTO
from src.modules.runtime_record.application.queries import ReadRuntimeValuesQuery
from src.modules.runtime_record.domain.errors import (
    RuntimeDataSourceNotFoundError,
    RuntimeObjectNotFoundError,
    RuntimeRecordValidationError,
)
from src.modules.runtime_record.domain.repositories import RuntimeValueRepositoryProtocol
from src.modules.runtime_schema.domain.entities import FieldMetadata, ObjectMetadata
from src.modules.runtime_schema.domain.repositories import (
    DataSourceRepositoryProtocol,
    FieldMetadataRepositoryProtocol,
    ObjectMetadataRepositoryProtocol,
)
from src.modules.runtime_schema.domain.value_objects import FieldType
from src.modules.shared.db.uow import UnitOfWorkProtocol


class RuntimeRecordApplicationService:
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        object_metadata_repository: ObjectMetadataRepositoryProtocol,
        field_metadata_repository: FieldMetadataRepositoryProtocol,
        data_source_repository: DataSourceRepositoryProtocol,
        runtime_value_repository: RuntimeValueRepositoryProtocol,
    ):
        self._uow = uow
        self._object_metadata_repository = object_metadata_repository
        self._field_metadata_repository = field_metadata_repository
        self._data_source_repository = data_source_repository
        self._runtime_value_repository = runtime_value_repository

    async def write_values(
        self,
        command: WriteRuntimeValuesCommand,
    ) -> RuntimeRecordValuesDTO:
        if getattr(self._uow, "session", None) is None:
            async with self._uow:
                return await self._write_within_transaction(command)
        return await self._write_within_transaction(command)

    async def read_values(
        self,
        query: ReadRuntimeValuesQuery,
    ) -> RuntimeRecordValuesDTO:
        if getattr(self._uow, "session", None) is None:
            async with self._uow:
                return await self._read_within_transaction(query)
        return await self._read_within_transaction(query)

    async def _write_within_transaction(
        self,
        command: WriteRuntimeValuesCommand,
    ) -> RuntimeRecordValuesDTO:
        object_metadata, schema_name = await self._resolve_object_and_schema(
            tenant_id=command.tenant_id,
            object_name_singular=command.object_name_singular,
        )
        fields = await self._field_metadata_repository.list_by_object_metadata_id(
            object_metadata.id
        )
        active_fields = tuple(field for field in fields if field.is_active)
        validated_values = _validate_payload(
            payload=command.values,
            fields=active_fields,
        )

        await self._runtime_value_repository.write_values(
            schema_name=schema_name,
            table_name=_table_name_for_object(object_metadata),
            record_id=command.record_id,
            values=validated_values,
        )
        await self._uow.commit()

        return RuntimeRecordValuesDTO(
            tenant_id=command.tenant_id,
            object_name_singular=command.object_name_singular,
            record_id=command.record_id,
            values=validated_values,
        )

    async def _read_within_transaction(
        self,
        query: ReadRuntimeValuesQuery,
    ) -> RuntimeRecordValuesDTO:
        object_metadata, schema_name = await self._resolve_object_and_schema(
            tenant_id=query.tenant_id,
            object_name_singular=query.object_name_singular,
        )
        fields = await self._field_metadata_repository.list_by_object_metadata_id(
            object_metadata.id
        )
        active_fields = tuple(field for field in fields if field.is_active)
        field_names = tuple(field.name for field in active_fields)
        raw_values = await self._runtime_value_repository.read_values(
            schema_name=schema_name,
            table_name=_table_name_for_object(object_metadata),
            record_id=query.record_id,
            field_names=field_names,
        )
        normalized_values = _normalize_read_values(
            raw_values=raw_values,
            fields=active_fields,
        )

        return RuntimeRecordValuesDTO(
            tenant_id=query.tenant_id,
            object_name_singular=query.object_name_singular,
            record_id=query.record_id,
            values=normalized_values,
        )

    async def _resolve_object_and_schema(
        self,
        *,
        tenant_id: UUID,
        object_name_singular: str,
    ) -> tuple[ObjectMetadata, str]:
        object_metadata = await self._object_metadata_repository.get_by_name(
            tenant_id=tenant_id,
            name_singular=object_name_singular,
        )
        if object_metadata is None:
            raise RuntimeObjectNotFoundError(
                tenant_id=tenant_id,
                object_name_singular=object_name_singular,
            )

        data_source = await self._data_source_repository.get_by_id(
            object_metadata.data_source_id
        )
        if data_source is None:
            raise RuntimeDataSourceNotFoundError(object_metadata.data_source_id)

        return object_metadata, data_source.schema


def _table_name_for_object(object_metadata: ObjectMetadata) -> str:
    if object_metadata.name_plural:
        return object_metadata.name_plural
    return f"{object_metadata.name_singular}s"


def _validate_payload(
    *,
    payload: dict[str, object | None],
    fields: tuple[FieldMetadata, ...],
) -> dict[str, object | None]:
    field_map = {field.name: field for field in fields}

    unknown_fields = sorted(name for name in payload if name not in field_map)
    if unknown_fields:
        raise RuntimeRecordValidationError(
            f"Unknown custom fields: {', '.join(unknown_fields)}."
        )

    for field in fields:
        if field.is_nullable:
            continue
        if field.name not in payload or payload[field.name] is None:
            raise RuntimeRecordValidationError(
                f"Field '{field.name}' is required (isNullable=false)."
            )

    validated: dict[str, object | None] = {}
    for name, value in payload.items():
        field = field_map[name]
        validated[name] = _validate_single_value(field=field, value=value)

    return validated


def _validate_single_value(*, field: FieldMetadata, value: object | None) -> object | None:
    if value is None:
        if not field.is_nullable:
            raise RuntimeRecordValidationError(
                f"Field '{field.name}' does not allow null."
            )
        return None

    if field.type == FieldType.PK:
        return _validate_uuid(field_name=field.name, value=value)
    if field.type in {FieldType.STRING, FieldType.LARGE_TEXT}:
        return _validate_string(field_name=field.name, value=value)
    if field.type == FieldType.NUMBER:
        return _validate_number(field_name=field.name, value=value)
    if field.type == FieldType.BOOLEAN:
        return _validate_boolean(field_name=field.name, value=value)
    if field.type == FieldType.DATE:
        return _validate_date(field_name=field.name, value=value)
    if field.type == FieldType.DATETIME:
        return _validate_datetime(field_name=field.name, value=value)
    if field.type == FieldType.SELECT:
        return _validate_select(
            field_name=field.name,
            value=value,
            options=field.options,
        )
    if field.type == FieldType.MULTISELECT:
        return _validate_multiselect(
            field_name=field.name,
            value=value,
            options=field.options,
        )

    raise RuntimeRecordValidationError(
        f"Unsupported field type for '{field.name}': '{field.type.value}'."
    )


def _validate_uuid(*, field_name: str, value: object) -> str:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, str):
        try:
            return str(UUID(value.strip()))
        except ValueError as exc:
            raise RuntimeRecordValidationError(
                f"Field '{field_name}' must be UUID."
            ) from exc
    raise RuntimeRecordValidationError(f"Field '{field_name}' must be UUID.")


def _validate_string(*, field_name: str, value: object) -> str:
    if not isinstance(value, str):
        raise RuntimeRecordValidationError(f"Field '{field_name}' must be string.")
    return value


def _validate_number(*, field_name: str, value: object) -> int | float | Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise RuntimeRecordValidationError(f"Field '{field_name}' must be numeric.")
    return value


def _validate_boolean(*, field_name: str, value: object) -> bool:
    if not isinstance(value, bool):
        raise RuntimeRecordValidationError(f"Field '{field_name}' must be boolean.")
    return value


def _validate_date(*, field_name: str, value: object) -> str:
    if isinstance(value, datetime):
        raise RuntimeRecordValidationError(
            f"Field '{field_name}' must be date without time."
        )
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            date.fromisoformat(value.strip())
        except ValueError as exc:
            raise RuntimeRecordValidationError(
                f"Field '{field_name}' must be ISO date."
            ) from exc
        return value.strip()
    raise RuntimeRecordValidationError(f"Field '{field_name}' must be date.")


def _validate_datetime(*, field_name: str, value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        normalized = value.strip()
        parsed = normalized[:-1] + "+00:00" if normalized.endswith("Z") else normalized
        try:
            datetime.fromisoformat(parsed)
        except ValueError as exc:
            raise RuntimeRecordValidationError(
                f"Field '{field_name}' must be ISO datetime."
            ) from exc
        return normalized
    raise RuntimeRecordValidationError(f"Field '{field_name}' must be datetime.")


def _validate_select(*, field_name: str, value: object, options: tuple[str, ...]) -> str:
    normalized = _validate_string(field_name=field_name, value=value)
    if options and normalized not in options:
        raise RuntimeRecordValidationError(
            f"Field '{field_name}' value '{normalized}' is not in options."
        )
    return normalized


def _validate_multiselect(
    *,
    field_name: str,
    value: object,
    options: tuple[str, ...],
) -> list[str]:
    if not isinstance(value, (list, tuple)):
        raise RuntimeRecordValidationError(
            f"Field '{field_name}' must be list[str] for MULTISELECT."
        )

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise RuntimeRecordValidationError(
                f"Field '{field_name}' must contain only strings."
            )
        normalized.append(item)

    if options:
        invalid = [item for item in normalized if item not in options]
        if invalid:
            raise RuntimeRecordValidationError(
                f"Field '{field_name}' has unsupported options: {', '.join(invalid)}."
            )

    return normalized


def _normalize_read_values(
    *,
    raw_values: dict[str, object | None],
    fields: tuple[FieldMetadata, ...],
) -> dict[str, object | None]:
    field_map = {field.name: field for field in fields}
    normalized: dict[str, object | None] = {}

    for name, value in raw_values.items():
        field = field_map.get(name)
        if field is None:
            normalized[name] = value
            continue

        if field.type == FieldType.MULTISELECT and isinstance(value, str):
            try:
                decoded = json.loads(value)
            except ValueError:
                normalized[name] = value
                continue
            normalized[name] = decoded if isinstance(decoded, list) else value
            continue

        normalized[name] = value

    return normalized


__all__ = ["RuntimeRecordApplicationService"]
