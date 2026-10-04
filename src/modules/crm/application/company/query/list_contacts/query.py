from dataclasses import dataclass

from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO


@dataclass(frozen=True, slots=True)
class ListCompanyContactsQuery:
    company_id: CompanyIdVO
