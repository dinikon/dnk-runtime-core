from __future__ import annotations

from src.modules.shared.db.uow import UnitOfWorkProtocol
from src.modules.runtime_schema.application.commands import DeleteCustomFieldCommand
from src.modules.runtime_schema.application.dto import DeleteCustomFieldResultDTO
from src.modules.runtime_schema.application.ports import (
    RuntimeSchemaFieldOrchestratorProtocol,
)
from src.modules.runtime_schema.domain.errors import (
    FieldMetadataNotFoundError,
    ObjectMetadataNotFoundError,
)
from src.modules.runtime_schema.domain.repositories import (
    FieldMetadataRepositoryProtocol,
    ObjectMetadataRepositoryProtocol,
)


class DeleteCustomFieldUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        field_metadata_repository: FieldMetadataRepositoryProtocol,
        object_metadata_repository: ObjectMetadataRepositoryProtocol,
        field_orchestrator: RuntimeSchemaFieldOrchestratorProtocol,
    ):
        self._uow = uow
        self._field_metadata_repository = field_metadata_repository
        self._object_metadata_repository = object_metadata_repository
        self._field_orchestrator = field_orchestrator

    async def execute(
        self,
        command: DeleteCustomFieldCommand,
    ) -> DeleteCustomFieldResultDTO:
        if getattr(self._uow, "session", None) is None:
            async with self._uow:
                return await self._delete_within_transaction(command)
        return await self._delete_within_transaction(command)

    async def _delete_within_transaction(
        self,
        command: DeleteCustomFieldCommand,
    ) -> DeleteCustomFieldResultDTO:
        field_metadata = await self._field_metadata_repository.get_by_id(
            command.field_metadata_id
        )
        if field_metadata is None:
            raise FieldMetadataNotFoundError(command.field_metadata_id)

        object_metadata = await self._object_metadata_repository.get_by_id(
            field_metadata.object_metadata_id
        )
        if object_metadata is None:
            raise ObjectMetadataNotFoundError(str(field_metadata.object_metadata_id))

        if command.hard_delete:
            await self._field_orchestrator.on_field_deleted(
                object_metadata=object_metadata,
                field_metadata=field_metadata,
                hard_delete=True,
            )
            deleted = await self._field_metadata_repository.delete_by_id(
                command.field_metadata_id
            )
            await self._uow.commit()
            return DeleteCustomFieldResultDTO(
                field_metadata_id=command.field_metadata_id,
                hard_delete=True,
                deleted=deleted,
                is_active=False,
            )

        deactivated = field_metadata.deactivate()
        await self._field_metadata_repository.deactivate(deactivated)
        await self._field_orchestrator.on_field_deleted(
            object_metadata=object_metadata,
            field_metadata=deactivated,
            hard_delete=False,
        )
        await self._uow.commit()

        return DeleteCustomFieldResultDTO(
            field_metadata_id=command.field_metadata_id,
            hard_delete=False,
            deleted=False,
            is_active=deactivated.is_active,
        )


__all__ = ["DeleteCustomFieldUseCase"]
