from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from src.modules.custom_object.application.command import (
    AddCustomFieldCommand,
    CreateCustomObjectCommand,
    CreateCustomRecordCommand,
    CustomObjectByIdCommand,
    CustomRecordByIdCommand,
    DeleteCustomFieldCommand,
    ListCustomRecordsQuery,
    UpdateCustomRecordCommand,
)
from src.modules.custom_object.application.dto import (
    CustomObjectDTO,
    CustomRecordDTO,
)
from src.modules.custom_object.application.ports import CustomObjectStoreProtocol
from src.modules.custom_object.domain import (
    CustomObjectRecordNotFoundError,
    CustomObjectValidationError,
)
from src.modules.runtime_data import PageSpec
from src.modules.runtime_data.application.ports import (
    RuntimeCommandGateway,
    RuntimeQueryGateway,
)
from src.modules.schema_registry.runtime import RuntimeObjectDescriptor
from src.modules.shared import TenantIdVO


class ListCustomObjectsUseCase:
    """Use case списка кастомных объектов tenant."""

    def __init__(self, store: CustomObjectStoreProtocol) -> None:
        """Инициализирует use case store-портом custom objects."""
        self._store = store

    async def __call__(self, *, tenant_id: TenantIdVO) -> list[CustomObjectDTO]:
        """Возвращает список кастомных объектов tenant."""
        return await self._store.list_objects(tenant_id=tenant_id)


class CreateCustomObjectUseCase:
    """Use case создания кастомного объекта."""

    def __init__(self, store: CustomObjectStoreProtocol) -> None:
        """Инициализирует use case store-портом custom objects."""
        self._store = store

    async def __call__(self, command: CreateCustomObjectCommand) -> CustomObjectDTO:
        """Создает кастомный объект."""
        return await self._store.create_object(command)


class DescribeCustomObjectUseCase:
    """Use case чтения схемы кастомного объекта."""

    def __init__(self, store: CustomObjectStoreProtocol) -> None:
        """Инициализирует use case store-портом custom objects."""
        self._store = store

    async def __call__(self, command: CustomObjectByIdCommand) -> CustomObjectDTO:
        """Возвращает схему кастомного объекта."""
        return await self._store.describe_object(
            tenant_id=command.tenant_id,
            object_id=command.object_id,
        )


class DeleteCustomObjectUseCase:
    """Use case hard delete кастомного объекта."""

    def __init__(self, store: CustomObjectStoreProtocol) -> None:
        """Инициализирует use case store-портом custom objects."""
        self._store = store

    async def __call__(self, command: CustomObjectByIdCommand) -> None:
        """Удаляет кастомный объект."""
        await self._store.delete_object(
            tenant_id=command.tenant_id,
            object_id=command.object_id,
        )


class AddCustomFieldUseCase:
    """Use case добавления custom field."""

    def __init__(self, store: CustomObjectStoreProtocol) -> None:
        """Инициализирует use case store-портом custom objects."""
        self._store = store

    async def __call__(self, command: AddCustomFieldCommand) -> CustomObjectDTO:
        """Добавляет custom field."""
        return await self._store.add_field(command)


class DeleteCustomFieldUseCase:
    """Use case удаления custom field."""

    def __init__(self, store: CustomObjectStoreProtocol) -> None:
        """Инициализирует use case store-портом custom objects."""
        self._store = store

    async def __call__(self, command: DeleteCustomFieldCommand) -> CustomObjectDTO:
        """Удаляет custom field."""
        return await self._store.delete_field(command)


class CreateCustomRecordUseCase:
    """Use case создания runtime-записи кастомного объекта."""

    def __init__(
        self,
        store: CustomObjectStoreProtocol,
        command_gateway: RuntimeCommandGateway,
    ) -> None:
        """Инициализирует use case store-портом и command gateway."""
        self._store = store
        self._command_gateway = command_gateway

    async def __call__(self, command: CreateCustomRecordCommand) -> CustomRecordDTO:
        """Создает runtime-запись кастомного объекта."""
        descriptor = await self._store.resolve_descriptor(
            tenant_id=command.tenant_id,
            object_id=command.object_id,
        )
        _ensure_no_system_values(descriptor=descriptor, values=command.values)
        row = await self._command_gateway.insert(
            descriptor=descriptor,
            payload=dict(command.values),
        )
        return _record_to_dto(
            descriptor=descriptor,
            object_id=command.object_id.uuid,
            row=row,
        )


class GetCustomRecordUseCase:
    """Use case чтения runtime-записи кастомного объекта."""

    def __init__(
        self,
        store: CustomObjectStoreProtocol,
        query_gateway: RuntimeQueryGateway,
    ) -> None:
        """Инициализирует use case store-портом и query gateway."""
        self._store = store
        self._query_gateway = query_gateway

    async def __call__(self, command: CustomRecordByIdCommand) -> CustomRecordDTO:
        """Возвращает runtime-запись кастомного объекта."""
        descriptor = await self._store.resolve_descriptor(
            tenant_id=command.tenant_id,
            object_id=command.object_id,
        )
        row = await self._query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=command.row_id,
        )
        if row is None:
            raise CustomObjectRecordNotFoundError("Custom object record was not found.")
        return _record_to_dto(
            descriptor=descriptor,
            object_id=command.object_id.uuid,
            row=row,
        )


class ListCustomRecordsUseCase:
    """Use case списка runtime-записей кастомного объекта."""

    def __init__(
        self,
        store: CustomObjectStoreProtocol,
        query_gateway: RuntimeQueryGateway,
    ) -> None:
        """Инициализирует use case store-портом и query gateway."""
        self._store = store
        self._query_gateway = query_gateway

    async def __call__(self, query: ListCustomRecordsQuery) -> list[CustomRecordDTO]:
        """Возвращает runtime-записи кастомного объекта."""
        descriptor = await self._store.resolve_descriptor(
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
            _record_to_dto(
                descriptor=descriptor,
                object_id=query.object_id.uuid,
                row=row,
            )
            for row in rows
        ]


class UpdateCustomRecordUseCase:
    """Use case обновления runtime-записи кастомного объекта."""

    def __init__(
        self,
        store: CustomObjectStoreProtocol,
        command_gateway: RuntimeCommandGateway,
    ) -> None:
        """Инициализирует use case store-портом и command gateway."""
        self._store = store
        self._command_gateway = command_gateway

    async def __call__(self, command: UpdateCustomRecordCommand) -> CustomRecordDTO:
        """Обновляет runtime-запись кастомного объекта."""
        descriptor = await self._store.resolve_descriptor(
            tenant_id=command.tenant_id,
            object_id=command.object_id,
        )
        _ensure_no_system_values(descriptor=descriptor, values=command.values)
        row = await self._command_gateway.update(
            descriptor=descriptor,
            object_id=command.row_id,
            patch=dict(command.values),
        )
        if row is None:
            raise CustomObjectRecordNotFoundError("Custom object record was not found.")
        return _record_to_dto(
            descriptor=descriptor,
            object_id=command.object_id.uuid,
            row=row,
        )


class DeleteCustomRecordUseCase:
    """Use case удаления runtime-записи кастомного объекта."""

    def __init__(
        self,
        store: CustomObjectStoreProtocol,
        command_gateway: RuntimeCommandGateway,
    ) -> None:
        """Инициализирует use case store-портом и command gateway."""
        self._store = store
        self._command_gateway = command_gateway

    async def __call__(self, command: CustomRecordByIdCommand) -> None:
        """Удаляет runtime-запись кастомного объекта."""
        descriptor = await self._store.resolve_descriptor(
            tenant_id=command.tenant_id,
            object_id=command.object_id,
        )
        deleted = await self._command_gateway.delete(
            descriptor=descriptor,
            object_id=command.row_id,
        )
        if not deleted:
            raise CustomObjectRecordNotFoundError("Custom object record was not found.")


def _record_to_dto(
    *,
    descriptor: RuntimeObjectDescriptor,
    object_id: UUID,
    row: Mapping[str, Any],
) -> CustomRecordDTO:
    row_id = _as_uuid(row.get(descriptor.pk))
    return CustomRecordDTO(
        object_id=object_id,
        row_id=row_id,
        values=dict(row),
    )


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


def _as_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        return UUID(value)
    raise TypeError("Custom object runtime row must contain UUID primary key.")
