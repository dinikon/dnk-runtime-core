from dataclasses import dataclass

from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.crm.domain.contact.error import InvalidContactCompanyLinkError
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO


@dataclass(frozen=True, slots=True)
class ContactCompanyLinkVO:
    """Одна связь Contact–Company, определяемая составным ключом."""

    contact_id: ContactIdVO
    company_id: CompanyIdVO

    def __post_init__(self) -> None:
        if not isinstance(self.contact_id, ContactIdVO) or not isinstance(
            self.company_id, CompanyIdVO
        ):
            raise InvalidContactCompanyLinkError(
                "Связь требует ContactIdVO и CompanyIdVO."
            )
