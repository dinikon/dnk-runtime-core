from __future__ import annotations

from typing import Protocol

from src.modules.custom_object.application.command import (
    AddCustomFieldCommand,
    CreateCustomObjectCommand,
    DeleteCustomFieldCommand,
)
from src.modules.custom_object.application.dto import CustomObjectDTO
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.runtime import RuntimeObjectDescriptor
from src.modules.shared import TenantIdVO


class CustomObjectStoreProtocol(Protocol):
    """Порт metadata + targeted DDL операций кастомных объектов."""

    async def list_objects(self, *, tenant_id: TenantIdVO) -> list[CustomObjectDTO]:
        """Возвращает список кастомных объектов tenant."""
        ...

    async def describe_object(
        self,
        *,
        tenant_id: TenantIdVO,
        object_id: RuntimeObjectIdVO,
    ) -> CustomObjectDTO:
        """Возвращает схему кастомного объекта tenant."""
        ...

    async def create_object(
        self,
        command: CreateCustomObjectCommand,
    ) -> CustomObjectDTO:
        """Создает metadata и физическую таблицу кастомного объекта."""
        ...

    async def delete_object(
        self,
        *,
        tenant_id: TenantIdVO,
        object_id: RuntimeObjectIdVO,
    ) -> None:
        """Удаляет metadata и физическую таблицу кастомного объекта."""
        ...

    async def add_field(
        self,
        command: AddCustomFieldCommand,
    ) -> CustomObjectDTO:
        """Добавляет custom field metadata и физическую колонку."""
        ...

    async def delete_field(
        self,
        command: DeleteCustomFieldCommand,
    ) -> CustomObjectDTO:
        """Удаляет custom field metadata и физическую колонку."""
        ...

    async def resolve_descriptor(
        self,
        *,
        tenant_id: TenantIdVO,
        object_id: RuntimeObjectIdVO,
    ) -> RuntimeObjectDescriptor:
        """Возвращает runtime descriptor кастомного объекта по object_id."""
        ...
