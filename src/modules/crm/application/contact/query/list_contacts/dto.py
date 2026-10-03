from dataclasses import dataclass

from src.modules.crm.application.contact.query.get_contact.dto import ContactDetailsDTO


@dataclass(frozen=True, slots=True)
class ListContactsResultDTO:
    """Полный список контактов текущего tenant."""

    contacts: tuple[ContactDetailsDTO, ...]
