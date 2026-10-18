from dataclasses import dataclass

from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListCompanyContactPointsQuery:
    tenant_id: EntityIdVO
    company_id: CompanyIdVO
