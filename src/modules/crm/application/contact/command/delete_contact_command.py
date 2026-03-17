from dataclasses import dataclass
from uuid import UUID

from src.modules.crm.domain.contact.value_object.contact_id import ContactIdVO


@dataclass(slots=True, frozen=True)
class DeleteContactCommand:
    tenant_id: UUID
    contact_id: ContactIdVO
