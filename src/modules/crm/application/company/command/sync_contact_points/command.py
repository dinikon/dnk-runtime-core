from dataclasses import dataclass

from src.modules.crm.application.contact_point.dto import ContactPointDraftDTO
from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class SyncCompanyContactPointsCommand:
    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    company_id: CompanyIdVO
    phones: tuple[ContactPointDraftDTO, ...] | None
    emails: tuple[ContactPointDraftDTO, ...] | None
