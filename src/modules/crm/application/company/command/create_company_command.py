from src.modules.crm.domain.contact.value_object import ContactIdVO
from dataclasses import dataclass
from src.modules.crm.application.contact_points.port import ContactPointInputDTO

from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class CreateCompanyCommand:
    """Входные данные создания компании."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    company_id: CompanyIdVO
    name: str
    phones: tuple[ContactPointInputDTO, ...] | None = None
    emails: tuple[ContactPointInputDTO, ...] | None = None
    contact_ids: tuple[ContactIdVO, ...] | None = None


__all__ = ["CreateCompanyCommand"]
