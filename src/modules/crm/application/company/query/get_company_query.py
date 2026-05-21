from dataclasses import dataclass

from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class GetCompanyQuery:
    """Query application-слоя на получение одной компании."""

    tenant_id: EntityIdVO
    company_id: CompanyIdVO
