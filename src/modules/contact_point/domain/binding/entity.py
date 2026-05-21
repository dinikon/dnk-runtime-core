from dataclasses import dataclass
from datetime import datetime

from src.modules.contact_point.domain.binding.value_object.owner_binding import (
    OwnerContactPointBinding,
)
from src.modules.shared import EntityIdVO
from src.modules.contact_point.domain.binding.value_object.contact_point_binding_id import (
    ContactPointBindingIdVO,
)


@dataclass(slots=True)
class ContactPointBindingEntity:
    id: ContactPointBindingIdVO
    created_at: datetime
    updated_at: datetime

    contact_point_id: EntityIdVO

    owner: OwnerContactPointBinding

    is_primary: bool

    detached_at: datetime | None
    is_active: bool
