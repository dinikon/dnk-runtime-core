from __future__ import annotations

from src.modules.shared.db.uow import UnitOfWorkProtocol
from src.modules.runtime_schema.application.commands import CreateCustomFieldCommand
from src.modules.runtime_schema.application.dto import FieldMetadataDTO
from src.modules.runtime_schema.application.mappers import field_metadata_to_dto
from src.modules.runtime_schema.application.ports import (
    RuntimeSchemaFieldOrchestratorProtocol,
)
from src.modules.runtime_schema.domain.entities import FieldMetadata
from src.modules.runtime_schema.domain.errors import ObjectMetadataNotFoundError
from src.modules.runtime_schema.domain.repositories import (
    FieldMetadataRepositoryProtocol,
    ObjectMetadataRepositoryProtocol,
)


class CreateCustomFieldUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        object_metadata_repository: ObjectMetadataRepositoryProtocol,
        field_metadata_repository: FieldMetadataRepositoryProtocol,
        field_orchestrator: RuntimeSchemaFieldOrchestratorProtocol,
    ):
        self._uow = uow
        self._object_metadata_repository = object_metadata_repository
        self._field_metadata_repository = field_metadata_repository
        self._field_orchestrator = field_orchestrator

    async def execute(self, command: CreateCustomFieldCommand) -> FieldMetadataDTO:
        if getattr(self._uow, "session", None) is None:
            async with self._uow:
                return await self._create_within_transaction(command)
        return await self._create_within_transaction(command)

    async def _create_within_transaction(
        self,
        command: CreateCustomFieldCommand,
    ) -> FieldMetadataDTO:
        object_metadata = await self._object_metadata_repository.get_by_id(
            command.object_metadata_id
        )
        if object_metadata is None:
            raise ObjectMetadataNotFoundError(str(command.object_metadata_id))

        field_metadata = FieldMetadata.create(
            object_metadata_id=command.object_metadata_id,
            tenant_id=command.tenant_id,
            field_type=command.field_type,
            name=command.name,
            label=command.label,
            default_value=command.default_value,
            description=command.description,
            icon=command.icon,
            options=command.options,
            settings=command.settings,
            is_active=command.is_active,
            is_nullable=command.is_nullable,
            is_unique=command.is_unique,
        )

        await self._field_metadata_repository.add(field_metadata)
        await self._field_orchestrator.on_field_created(
            object_metadata=object_metadata,
            field_metadata=field_metadata,
        )
        await self._uow.commit()

        return field_metadata_to_dto(field_metadata)


__all__ = ["CreateCustomFieldUseCase"]
