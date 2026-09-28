from src.modules.crm.application.company.query.repository import (
    CompanyQueryRepositoryProtocol,
)
from src.modules.crm.application.company.query.list_available_companies_query import (
    ListAvailableCompaniesQuery,
)
from src.modules.crm.domain.contact.error import ContactNotFoundError


class ListAvailableCompaniesUseCase:
    def __init__(self, repository: CompanyQueryRepositoryProtocol):
        self.repository = repository

    async def __call__(self, query: ListAvailableCompaniesQuery):
        page = await self.repository.list_available(query)
        if page is None:
            raise ContactNotFoundError("Contact not found.")
        return page
