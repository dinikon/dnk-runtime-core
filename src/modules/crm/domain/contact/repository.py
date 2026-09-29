from typing import Protocol

from src.modules.crm.domain.contact.aggregate import Contact
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ContactRepositoryProtocol(Protocol):
    """Контракт сохранения нового контакта в текущей транзакции tenant."""

    async def add(self, tenant_id: EntityIdVO, contact: Contact) -> None:
        """Добавляет контакт без самостоятельного завершения транзакции."""
        ...
