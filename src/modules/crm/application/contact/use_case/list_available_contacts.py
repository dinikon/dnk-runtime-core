from src.modules.crm.application.contact.query.repository import (
    ContactQueryRepositoryProtocol,
)
from src.modules.crm.application.contact.query.list_available_contacts_query import (
    ListAvailableContactsQuery,
)
from src.modules.crm.domain.company.error import CompanyNotFoundError


class ListAvailableContactsUseCase:
    def __init__(self, repository: ContactQueryRepositoryProtocol):
        self.repository = repository

    async def __call__(self, query: ListAvailableContactsQuery):
        page = await self.repository.list_available(query)
        if page is None:
            raise CompanyNotFoundError("Company not found.")
        return page
