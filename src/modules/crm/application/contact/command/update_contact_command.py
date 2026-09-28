from src.modules.crm.domain.company.value_object import CompanyIdVO
from dataclasses import dataclass
from src.modules.crm.application.contact_points.port import ContactPointInputDTO

from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class UpdateContactCommand:
    """Входные данные полного обновления контакта."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    contact_id: ContactIdVO
    first_name: str
    last_name: str | None = None
    middle_name: str | None = None
    phones: tuple[ContactPointInputDTO, ...] | None = None
    emails: tuple[ContactPointInputDTO, ...] | None = None
    company_ids: tuple[CompanyIdVO, ...] | None = None
    expected_company_ids: tuple[CompanyIdVO, ...] | None = None


__all__ = ["UpdateContactCommand"]
