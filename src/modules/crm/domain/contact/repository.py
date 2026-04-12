from typing import Protocol

from src.modules.crm.domain.contact.entity import ContactEntity
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.shared import EntityIdVO


class ContactCommandRepositoryProtocol(Protocol):
    """Порт командного хранения CRM-контактов."""

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_id: ContactIdVO,
    ) -> ContactEntity | None:
        """Загружает контакт tenant по id или возвращает None."""
        ...

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        contact: ContactEntity,
    ) -> ContactEntity:
        """Сохраняет контакт tenant и возвращает актуальную entity."""
        ...

    async def delete(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_id: ContactIdVO,
    ) -> None:
        """Удаляет контакт tenant по id."""
        ...
