from src.modules.crm.application.contact.port.query_repository import (
    ContactQueryRepositoryProtocol,
)
from src.modules.crm.application.contact.query.list_contacts.dto import (
    ListContactsResultDTO,
)
from src.modules.crm.application.contact.query.list_contacts.query import (
    ListContactsQuery,
)


class ListContactsHandler:
    """Возвращает все проекции контактов текущего tenant."""

    def __init__(self, repository: ContactQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def execute(self, query: ListContactsQuery) -> ListContactsResultDTO:
        return ListContactsResultDTO(tuple(await self._repository.list_details()))
