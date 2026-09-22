from src.modules.crm.application.contact.dto import ContactPageDTO
from src.modules.crm.application.contact.query import (
    ContactQueryRepositoryProtocol,
    ListContactsQuery,
)


class ListContactsUseCase:
    """Возвращает найденную страницу контактов."""

    def __init__(self, repository: ContactQueryRepositoryProtocol):
        self.repository = repository

    async def __call__(self, query: ListContactsQuery) -> ContactPageDTO:
        """Передаёт типизированный запрос в query repository."""
        return await self.repository.list(query)


__all__ = ["ListContactsUseCase"]
