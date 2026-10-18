from src.modules.crm.application.company.port.query_repository import (
    CompanyQueryRepositoryProtocol,
)
from src.modules.crm.application.company.query.get_company.dto import CompanyDetailsDTO
from src.modules.crm.application.company.query.get_company.query import GetCompanyQuery
from src.modules.crm.domain.company.error import CompanyNotFoundError


class GetCompanyHandler:
    def __init__(self, repository: CompanyQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def execute(self, query: GetCompanyQuery) -> CompanyDetailsDTO:
        result = await self._repository.get_details(company_id=query.company_id)
        if result is None:
            raise CompanyNotFoundError("Company not found.")
        return result
