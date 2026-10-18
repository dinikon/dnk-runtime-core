from src.modules.crm.application.company.command.delete_company.command import (
    DeleteCompanyCommand,
)
from src.modules.crm.application.contact_point.port import ContactPointsPort
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.company.repository import CompanyRepositoryProtocol


class DeleteCompanyHandler:
    def __init__(
        self, repository: CompanyRepositoryProtocol, points: ContactPointsPort
    ) -> None:
        self._repository = repository
        self._points = points

    async def execute(self, command: DeleteCompanyCommand) -> None:
        company = await self._repository.get_for_update(command.company_id)
        if company is None:
            raise CompanyNotFoundError("Company not found.")
        await self._points.remove(command.tenant_id, command.company_id)
        await self._repository.delete(company)
