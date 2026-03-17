from __future__ import annotations

from src.modules.crm.application.commands import DeleteCompanyCommand
from src.modules.crm.application.dto import DeleteCompanyResultDTO
from src.modules.crm.domain.errors import CompanyNotFoundError
from src.modules.crm.domain.repositories import CompanyRepositoryProtocol
from src.modules.shared.db.uow import UnitOfWorkProtocol


class DeleteCompanyUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        company_repository: CompanyRepositoryProtocol,
    ):
        self._uow = uow
        self._company_repository = company_repository

    async def execute(self, command: DeleteCompanyCommand) -> DeleteCompanyResultDTO:
        if getattr(self._uow, "session", None) is None:
            async with self._uow:
                return await self._delete_within_transaction(command)
        return await self._delete_within_transaction(command)

    async def _delete_within_transaction(
        self,
        command: DeleteCompanyCommand,
    ) -> DeleteCompanyResultDTO:
        deleted = await self._company_repository.delete_by_id(command.company_id)
        if not deleted:
            raise CompanyNotFoundError(command.company_id)

        await self._uow.commit()
        return DeleteCompanyResultDTO(company_id=command.company_id, deleted=True)


__all__ = ["DeleteCompanyUseCase"]
