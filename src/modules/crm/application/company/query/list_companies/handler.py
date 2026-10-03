from src.modules.crm.application.company.port.query_repository import (
    CompanyQueryRepositoryProtocol,
)
from src.modules.crm.application.company.query.list_companies.dto import (
    ListCompaniesResultDTO,
)
from src.modules.crm.application.company.query.list_companies.query import (
    ListCompaniesQuery,
)


class ListCompaniesHandler:
    def __init__(self, repository: CompanyQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def execute(self, query: ListCompaniesQuery) -> ListCompaniesResultDTO:
        return ListCompaniesResultDTO(tuple(await self._repository.list_details()))
