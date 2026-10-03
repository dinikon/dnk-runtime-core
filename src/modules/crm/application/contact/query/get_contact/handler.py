from src.modules.crm.application.contact.port.query_repository import (
    ContactQueryRepositoryProtocol,
)
from src.modules.crm.application.contact.query.get_contact.dto import ContactDetailsDTO
from src.modules.crm.application.contact.query.get_contact.query import GetContactQuery
from src.modules.crm.domain.contact.error import ContactNotFoundError


class GetContactHandler:
    """Возвращает карточку контакта через независимый порт чтения."""

    def __init__(self, repository: ContactQueryRepositoryProtocol) -> None:
        """Получает порт проекций без доступа к SQL и транзакции."""
        self._repository = repository

    async def execute(self, query: GetContactQuery) -> ContactDetailsDTO:
        """Читает сохранённые данные либо сообщает об отсутствии контакта."""
        result = await self._repository.get_details(contact_id=query.contact_id)
        if result is None:
            raise ContactNotFoundError("Contact not found.")
        return result
