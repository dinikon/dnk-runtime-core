from dataclasses import dataclass

from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class DeleteCompanyCommand:
    """Параметры физического удаления компании."""

    tenant_id: EntityIdVO
    company_id: CompanyIdVO


__all__ = ["DeleteCompanyCommand"]
