from dataclasses import dataclass

from src.modules.crm.application.contact.query.get_contact.dto import ContactDetailsDTO


@dataclass(frozen=True, slots=True)
class ListCompanyContactsResultDTO:
    contacts: tuple[ContactDetailsDTO, ...]
