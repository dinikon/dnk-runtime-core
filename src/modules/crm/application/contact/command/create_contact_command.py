from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.crm.domain.contact.value_object.contact_id import ContactIdVO


@dataclass(slots=True, frozen=True)
class CreateContactCommand:
    contact_id: ContactIdVO
    tenant_id: UUID
    now: datetime
    last_name: str
    first_name: str | None = None
    middle_name: str | None = None
