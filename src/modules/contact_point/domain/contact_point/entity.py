from dataclasses import dataclass
from datetime import datetime

from src.modules.contact_point.domain.contact_point.value_object.contact_point_type import (
    ContactPointTypeVO,
)
from src.modules.contact_point.domain.contact_point.value_object.contact_point_id import (
    ContactPointIdVO,
)


@dataclass(slots=True)
class ContactPointEntity:

    id: ContactPointIdVO
    created_at: datetime
    updated_at: datetime

    contact_point_type: ContactPointTypeVO

    raw_value: str
    normalized_value: str

    hash_value: str
