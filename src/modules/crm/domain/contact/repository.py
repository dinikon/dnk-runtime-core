from typing import Protocol

from src.modules.crm.domain.contact.aggregate import ContactEntity


class ContactRepositoryProtocol(Protocol):
    """Контракт сохранения нового контакта в текущей транзакции tenant."""

    async def add(self, contact: ContactEntity) -> None:
        """Добавляет контакт без самостоятельного завершения транзакции."""
        ...
