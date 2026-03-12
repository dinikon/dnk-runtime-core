from __future__ import annotations

from src.modules.custom_object.application.commands import CreateCustomObjectFieldCommandDTO
from src.modules.custom_object.application.dto import CreateCustomObjectFieldResultDTO
from src.modules.custom_object.application.ports import (
    CreateCustomObjectFieldCommand,
    CustomObjectSchemaRepositoryPort,
)
from src.modules.custom_object.domain import (
    CustomObjectNameVO,
    CustomObjectRelationTargetRequiredError,
)


class CreateCustomObjectFieldUseCase:
    def __init__(self, repository: CustomObjectSchemaRepositoryPort):
        self._repository = repository

    async def execute(
        self,
        dto: CreateCustomObjectFieldCommandDTO,
    ) -> CreateCustomObjectFieldResultDTO:
        object_name = CustomObjectNameVO(dto.object_name_singular)
        field_type = dto.field_type.strip().lower()
        relation_target_object_name = dto.relation_target_object_name
        if field_type == "relation" and not relation_target_object_name:
            raise CustomObjectRelationTargetRequiredError(dto.field_name)

        settings = dict(dto.settings) if dto.settings is not None else {}
        if field_type == "relation" and "max_links" not in settings:
            settings["max_links"] = 1

        definition = await self._repository.create_field_definition(
            CreateCustomObjectFieldCommand(
                tenant_id=dto.tenant_id,
                object_name_singular=object_name.value,
                field_type=field_type,
                field_name=dto.field_name,
                label=dto.label,
                description=dto.description,
                icon=dto.icon,
                is_active=dto.is_active,
                is_unique=dto.is_unique,
                is_index=dto.is_index,
                is_nullable=dto.is_nullable,
                is_ui_read_only=dto.is_ui_read_only,
                is_searchable=dto.is_searchable,
                options=dto.options,
                settings=settings or None,
                default_value=dto.default_value,
                relation_target_object_name=relation_target_object_name,
                relation_target_field_id=dto.relation_target_field_id,
            )
        )
        return CreateCustomObjectFieldResultDTO(
            id=definition.id,
            object_id=definition.object_id,
            field_type=definition.field_type,
            field_name=definition.field_name,
            label=definition.label,
            description=definition.description,
            icon=definition.icon,
            is_active=definition.is_active,
            is_unique=definition.is_unique,
            is_index=definition.is_index,
            is_nullable=definition.is_nullable,
            is_ui_read_only=definition.is_ui_read_only,
            is_searchable=definition.is_searchable,
            created_at=definition.created_at,
            updated_at=definition.updated_at,
        )


__all__ = ["CreateCustomObjectFieldUseCase"]
