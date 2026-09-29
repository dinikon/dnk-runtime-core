from typing import Protocol

from src.modules.crm.application.contact.query.get_contact.dto import ContactDetailsDTO
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ContactQueryRepositoryProtocol(Protocol):
    """Порт чтения проекции контакта без восстановления доменного агрегата."""

    async def get_details(
        self, *, tenant_id: EntityIdVO, contact_id: ContactIdVO
    ) -> ContactDetailsDTO | None:
        """Возвращает запись текущего tenant либо None, если её нет."""
        ...
