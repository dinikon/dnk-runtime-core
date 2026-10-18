from src.modules.crm.application.company.port.contact_link_query_repository import (
    CompanyContactQueryRepositoryProtocol,
)
from src.modules.crm.application.company.query.list_contacts.dto import (
    ListCompanyContactsResultDTO,
)
from src.modules.crm.application.company.query.list_contacts.query import (
    ListCompanyContactsQuery,
)
from src.modules.crm.domain.company.error import CompanyNotFoundError


class ListCompanyContactsHandler:
    def __init__(self, repository: CompanyContactQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def execute(
        self, query: ListCompanyContactsQuery
    ) -> ListCompanyContactsResultDTO:
        contacts = await self._repository.list_contacts(query.company_id)
        if contacts is None:
            raise CompanyNotFoundError("Company not found.")
        return ListCompanyContactsResultDTO(tuple(contacts))
