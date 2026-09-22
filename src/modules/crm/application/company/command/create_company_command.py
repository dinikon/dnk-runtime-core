from dataclasses import dataclass

from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class CreateCompanyCommand:
    """Входные данные создания компании."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    company_id: CompanyIdVO
    name: str


__all__ = ["CreateCompanyCommand"]
