from typing import Protocol

from src.modules.crm.application.contact.dto.contact_dto import ContactDTO
from src.modules.crm.application.contact.query.list_contacts_query import (
    ListContactsQuery,
)
from src.modules.crm.application.contact.query.repository import (
    ContactQueryRepositoryProtocol,
)


class ListContactsUseCaseProtocol(Protocol):
    """Порт use case получения списка контактов."""

    async def __call__(self, query: ListContactsQuery) -> list[ContactDTO]:
        """Возвращает страницу контактов tenant."""
        ...


class ListContactsUseCase:
    """Use case чтения списка CRM-контактов через query repository."""

    def __init__(self, query_repository: ContactQueryRepositoryProtocol):
        """Инициализирует use case query-репозиторием контактов."""
        self._query_repository = query_repository

    async def __call__(self, query: ListContactsQuery) -> list[ContactDTO]:
        """Выполняет query списка контактов."""
        return await self._query_repository.list(
            tenant_id=query.tenant_id,
            limit=query.limit,
            offset=query.offset,
        )
