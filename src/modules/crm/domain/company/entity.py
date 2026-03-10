from dataclasses import dataclass

from modules.crm.domain.company.value_objects import CompanyId


@dataclass(slots=True)
class Company:
    id: CompanyId
    company_name: str
