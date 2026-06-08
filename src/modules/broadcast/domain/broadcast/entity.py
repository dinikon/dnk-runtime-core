from dataclasses import dataclass
from datetime import datetime

from src.modules.broadcast.domain.broadcast.value_object.broadcast_id import (
    BroadcastIdVO,
)
from src.modules.broadcast.domain.broadcast.value_object.broadcast_status import (
    BroadcastStatusVO,
)
from src.modules.shared.domain.value_object.entity_description import (
    EntityDescriptionVO,
)
from src.modules.shared.domain.value_object.entity_title import EntityTitleVO


@dataclass(slots=True)
class BroadcastEntity:
    id: BroadcastIdVO

    created_at: datetime
    updated_at: datetime | None

    title: EntityTitleVO
    description: EntityDescriptionVO | None

    status: BroadcastStatusVO
