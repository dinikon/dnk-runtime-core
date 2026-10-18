from src.modules.crm.application.contact.port.company_link_query_repository import (
    ContactCompanyQueryRepositoryProtocol,
)
from src.modules.crm.application.contact.query.list_companies.dto import (
    ListContactCompaniesResultDTO,
)
from src.modules.crm.application.contact.query.list_companies.query import (
    ListContactCompaniesQuery,
)
from src.modules.crm.domain.contact.error import ContactNotFoundError


class ListContactCompaniesHandler:
    def __init__(self, repository: ContactCompanyQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def execute(
        self, query: ListContactCompaniesQuery
    ) -> ListContactCompaniesResultDTO:
        companies = await self._repository.list_companies(query.contact_id)
        if companies is None:
            raise ContactNotFoundError("Contact not found.")
        return ListContactCompaniesResultDTO(tuple(companies))
