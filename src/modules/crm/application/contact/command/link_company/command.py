from dataclasses import dataclass

from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO


@dataclass(frozen=True, slots=True)
class LinkCompanyCommand:
    contact_id: ContactIdVO
    company_id: CompanyIdVO
