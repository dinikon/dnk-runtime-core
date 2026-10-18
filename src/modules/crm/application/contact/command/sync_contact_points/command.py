from dataclasses import dataclass

from src.modules.crm.application.contact_point.dto import ContactPointDraftDTO
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class SyncContactContactPointsCommand:
    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    contact_id: ContactIdVO
    phones: tuple[ContactPointDraftDTO, ...] | None
    emails: tuple[ContactPointDraftDTO, ...] | None
