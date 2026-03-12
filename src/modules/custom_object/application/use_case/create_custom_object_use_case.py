from __future__ import annotations

from src.modules.custom_object.application.commands import CreateCustomObjectCommandDTO
from src.modules.custom_object.application.dto import CreateCustomObjectResultDTO
from src.modules.custom_object.application.ports import (
    CreateCustomObjectDefinitionCommand,
    CustomObjectSchemaRepositoryPort,
)
from src.modules.custom_object.domain import CustomObjectNameVO


class CreateCustomObjectUseCase:
    def __init__(self, repository: CustomObjectSchemaRepositoryPort):
        self._repository = repository

    async def execute(
        self,
        dto: CreateCustomObjectCommandDTO,
    ) -> CreateCustomObjectResultDTO:
        object_name = CustomObjectNameVO(dto.object_name_singular)
        definition = await self._repository.create_object_definition(
            CreateCustomObjectDefinitionCommand(
                tenant_id=dto.tenant_id,
                object_name_singular=object_name.value,
                object_name_plural=dto.object_name_plural,
                object_label_singular=dto.object_label_singular,
                object_label_plural=dto.object_label_plural,
                description=dto.description,
                icon=dto.icon,
                shortcut=dto.shortcut,
                is_active=dto.is_active,
                is_ui_read_only=dto.is_ui_read_only,
            )
        )
        return CreateCustomObjectResultDTO(
            id=definition.id,
            object_name_singular=definition.object_name_singular,
            object_name_plural=definition.object_name_plural,
            object_label_singular=definition.object_label_singular,
            object_label_plural=definition.object_label_plural,
            description=definition.description,
            icon=definition.icon,
            shortcut=definition.shortcut,
            is_active=definition.is_active,
            is_ui_read_only=definition.is_ui_read_only,
            created_at=definition.created_at,
            updated_at=definition.updated_at,
        )


__all__ = ["CreateCustomObjectUseCase"]
