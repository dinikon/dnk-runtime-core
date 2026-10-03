from dataclasses import dataclass

from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO


@dataclass(frozen=True, slots=True)
class GetContactQuery:
    """Параметры чтения одного контакта в доверенном tenant-контексте."""

    contact_id: ContactIdVO
