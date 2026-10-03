from typing import Protocol

from src.modules.crm.domain.contact.aggregate import ContactEntity
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO


class ContactRepositoryProtocol(Protocol):
    """Контракт сохранения нового контакта в текущей транзакции tenant."""

    async def add(self, contact: ContactEntity) -> None:
        """Добавляет контакт без самостоятельного завершения транзакции."""
        ...

    async def get_for_update(self, contact_id: ContactIdVO) -> ContactEntity | None:
        """Загружает агрегат с блокировкой в текущей транзакции."""
        ...

    async def save(self, contact: ContactEntity) -> None:
        """Сохраняет изменённое ФИО и аудит."""
        ...

    async def delete(self, contact: ContactEntity) -> None:
        """Удаляет контакт из текущей tenant-схемы."""
        ...
