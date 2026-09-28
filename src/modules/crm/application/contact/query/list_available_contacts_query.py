from dataclasses import dataclass
from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListAvailableContactsQuery:
    tenant_id: EntityIdVO
    company_id: CompanyIdVO
    q: str = ""
    limit: int = 25
    offset: int = 0
