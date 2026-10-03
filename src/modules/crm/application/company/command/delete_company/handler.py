from src.modules.crm.application.company.command.delete_company.command import (
    DeleteCompanyCommand,
)
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.company.repository import CompanyRepositoryProtocol


class DeleteCompanyHandler:
    def __init__(self, repository: CompanyRepositoryProtocol) -> None:
        self._repository = repository

    async def execute(self, command: DeleteCompanyCommand) -> None:
        company = await self._repository.get_for_update(command.company_id)
        if company is None:
            raise CompanyNotFoundError("Company not found.")
        await self._repository.delete(company)
