from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from src.modules.custom_object.application.record.command import (
    CreateCustomRecordCommand,
    CustomRecordByIdCommand,
    UpdateCustomRecordCommand,
)
from src.modules.custom_object.application.record.dto import CustomRecordDTO
from src.modules.custom_object.application.record.query import ListCustomRecordsQuery
from src.modules.custom_object.application.record.repository import (
    CustomRecordRepositoryProtocol,
)
from src.modules.custom_object.domain import (
    CustomObjectRecordNotFoundError,
    CustomObjectValidationError,
)
from src.modules.runtime_data import PageSpec
from src.modules.runtime_data.application.ports import (
    RuntimeCommandGateway,
    RuntimeQueryGateway,
)
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.runtime import (
    RuntimeObjectDescriptor,
    RuntimeObjectResolverProtocol,
)
from src.modules.shared import EntityIdVO


class CustomRecordRuntimeRepository(CustomRecordRepositoryProtocol):
    """Runtime CRUD repository для записей custom object."""

    def __init__(
        self,
        *,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        command_gateway: RuntimeCommandGateway,
        query_gateway: RuntimeQueryGateway,
    ) -> None:
        """Инициализирует repository runtime resolver и gateway-портами."""
        self._runtime_object_resolver = runtime_object_resolver
        self._command_gateway = command_gateway
        self._query_gateway = query_gateway

    async def create(self, command: CreateCustomRecordCommand) -> CustomRecordDTO:
        """Создает runtime-запись кастомного объекта."""
        descriptor = await self._resolve_descriptor(
            tenant_id=command.tenant_id,
            object_id=command.object_id,
        )
        self._ensure_no_system_values(descriptor=descriptor, values=command.values)
        row = await self._command_gateway.insert(
            descriptor=descriptor,
            payload=dict(command.values),
        )
        return self._record_to_dto(
            descriptor=descriptor,
            object_id=command.object_id.uuid,
            row=row,
        )

    async def get(self, command: CustomRecordByIdCommand) -> CustomRecordDTO:
        """Возвращает runtime-запись кастомного объекта."""
        descriptor = await self._resolve_descriptor(
            tenant_id=command.tenant_id,
            object_id=command.object_id,
        )
        row = await self._query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=command.row_id,
        )
        if row is None:
            raise CustomObjectRecordNotFoundError("Custom object record was not found.")
        return self._record_to_dto(
            descriptor=descriptor,
            object_id=command.object_id.uuid,
            row=row,
        )

    async def list(self, query: ListCustomRecordsQuery) -> list[CustomRecordDTO]:
        """Возвращает runtime-записи кастомного объекта."""
        descriptor = await self._resolve_descriptor(
            tenant_id=query.tenant_id,
            object_id=query.object_id,
        )
        rows = await self._query_gateway.list(
            descriptor=descriptor,
            filters=query.filters,
            sorting=query.sorting,
            page=PageSpec(limit=query.limit, offset=query.offset),
        )
        return [
            self._record_to_dto(
                descriptor=descriptor,
                object_id=query.object_id.uuid,
                row=row,
            )
            for row in rows
        ]

    async def update(self, command: UpdateCustomRecordCommand) -> CustomRecordDTO:
        """Обновляет runtime-запись кастомного объекта."""
        descriptor = await self._resolve_descriptor(
            tenant_id=command.tenant_id,
            object_id=command.object_id,
        )
        self._ensure_no_system_values(descriptor=descriptor, values=command.values)
        row = await self._command_gateway.update(
            descriptor=descriptor,
            object_id=command.row_id,
            patch=dict(command.values),
        )
        if row is None:
            raise CustomObjectRecordNotFoundError("Custom object record was not found.")
        return self._record_to_dto(
            descriptor=descriptor,
            object_id=command.object_id.uuid,
            row=row,
        )

    async def delete(self, command: CustomRecordByIdCommand) -> None:
        """Удаляет runtime-запись кастомного объекта."""
        descriptor = await self._resolve_descriptor(
            tenant_id=command.tenant_id,
            object_id=command.object_id,
        )
        deleted = await self._command_gateway.delete(
            descriptor=descriptor,
            object_id=command.row_id,
        )
        if not deleted:
            raise CustomObjectRecordNotFoundError("Custom object record was not found.")

    async def _resolve_descriptor(
        self,
        *,
        tenant_id: EntityIdVO,
        object_id: RuntimeObjectIdVO,
    ) -> RuntimeObjectDescriptor:
        descriptor = await self._runtime_object_resolver.resolve_by_id(
            tenant_id=tenant_id,
            object_id=object_id,
        )
        if descriptor.kind.strip().lower() != "custom":
            raise CustomObjectValidationError(
                "Custom object record operations support only custom objects."
            )
        return descriptor

    @staticmethod
    def _record_to_dto(
        *,
        descriptor: RuntimeObjectDescriptor,
        object_id: UUID,
        row: Mapping[str, Any],
    ) -> CustomRecordDTO:
        row_id = CustomRecordRuntimeRepository._as_uuid(row.get(descriptor.pk))
        return CustomRecordDTO(
            object_id=object_id,
            row_id=row_id,
            values=dict(row),
        )

    @staticmethod
    def _ensure_no_system_values(
        *,
        descriptor: RuntimeObjectDescriptor,
        values: Mapping[str, Any],
    ) -> None:
        system_fields = {
            field.name
            for field in descriptor.fields
            if field.kind.strip().lower() == "system"
        }
        blocked_fields = sorted(set(values) & system_fields)
        if blocked_fields:
            raise CustomObjectValidationError(
                f"System fields cannot be written directly: {blocked_fields}."
            )

    @staticmethod
    def _as_uuid(value: Any) -> UUID:
        if isinstance(value, UUID):
            return value
        if isinstance(value, str):
            return UUID(value)
        raise TypeError("Custom object runtime row must contain UUID primary key.")


__all__ = ["CustomRecordRuntimeRepository"]
