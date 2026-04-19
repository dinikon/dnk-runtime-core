from typing import Protocol

from src.modules.crm.application.contact.dto.contact_fields_description_dto import (
    ContactFieldsDescriptionDTO,
)
from src.modules.shared import EntityIdVO


class ContactFieldsDescriptionRepositoryProtocol(Protocol):
    """Порт чтения описания CRM-модели контакта."""

    async def describe_fields(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> ContactFieldsDescriptionDTO:
        """Возвращает описание объекта contact и его полей для tenant."""
        ...


__all__ = ["ContactFieldsDescriptionRepositoryProtocol"]
