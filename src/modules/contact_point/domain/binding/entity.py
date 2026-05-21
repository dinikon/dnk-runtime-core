from dataclasses import dataclass
from datetime import datetime

from src.modules.contact_point.domain.binding.value_object.owner_binding import (
    OwnerContactPointBinding,
)
from src.modules.contact_point.domain.binding.value_object.contact_point_binding_id import (
    ContactPointBindingIdVO,
)
from src.modules.contact_point.domain.contact_point.value_object.contact_point_id import (
    ContactPointIdVO,
)
from src.modules.contact_point.domain.contact_point.value_object.contact_point_type import (
    ContactPointTypeVO,
)


@dataclass(slots=True)
class ContactPointBindingEntity:
    id: ContactPointBindingIdVO
    created_at: datetime
    updated_at: datetime

    contact_point_id: ContactPointIdVO
    contact_point_type: ContactPointTypeVO

    owner: OwnerContactPointBinding

    is_primary: bool

    detached_at: datetime | None
    is_active: bool

    @classmethod
    def create(
        cls,
        *,
        id_: ContactPointBindingIdVO,
        now: datetime,
        contact_point_id: ContactPointIdVO,
        contact_point_type: ContactPointTypeVO,
        owner: OwnerContactPointBinding,
        is_primary: bool,
    ) -> "ContactPointBindingEntity":
        return cls(
            id=id_,
            created_at=now,
            updated_at=now,
            contact_point_id=contact_point_id,
            contact_point_type=contact_point_type,
            owner=owner,
            is_primary=is_primary,
            detached_at=None,
            is_active=True,
        )

    def reactivate(self, *, now: datetime, is_primary: bool) -> None:
        self.is_active = True
        self.detached_at = None
        self.is_primary = is_primary
        self.updated_at = now

    def detach(self, *, now: datetime) -> None:
        self.is_active = False
        self.is_primary = False
        self.detached_at = now
        self.updated_at = now

    def mark_primary(self, *, now: datetime) -> None:
        self.is_primary = True
        self.updated_at = now

    def unmark_primary(self, *, now: datetime) -> None:
        self.is_primary = False
        self.updated_at = now
