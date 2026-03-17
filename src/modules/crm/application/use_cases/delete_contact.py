from __future__ import annotations

from src.modules.crm.application.commands import DeleteContactCommand
from src.modules.crm.application.dto import DeleteContactResultDTO
from src.modules.crm.domain.errors import ContactNotFoundError
from src.modules.crm.domain.repositories import ContactRepositoryProtocol
from src.modules.shared.db.uow import UnitOfWorkProtocol


class DeleteContactUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        contact_repository: ContactRepositoryProtocol,
    ):
        self._uow = uow
        self._contact_repository = contact_repository

    async def execute(self, command: DeleteContactCommand) -> DeleteContactResultDTO:
        if getattr(self._uow, "session", None) is None:
            async with self._uow:
                return await self._delete_within_transaction(command)
        return await self._delete_within_transaction(command)

    async def _delete_within_transaction(
        self,
        command: DeleteContactCommand,
    ) -> DeleteContactResultDTO:
        deleted = await self._contact_repository.delete_by_id(command.contact_id)
        if not deleted:
            raise ContactNotFoundError(command.contact_id)

        await self._uow.commit()
        return DeleteContactResultDTO(contact_id=command.contact_id, deleted=True)


__all__ = ["DeleteContactUseCase"]
