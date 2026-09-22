from dataclasses import dataclass

from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class GetCompanyQuery:
    """Параметры чтения компании."""

    tenant_id: EntityIdVO
    company_id: CompanyIdVO


__all__ = ["GetCompanyQuery"]
