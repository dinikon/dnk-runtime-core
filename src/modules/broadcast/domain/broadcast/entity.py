from dataclasses import dataclass
from datetime import datetime

from src.modules.broadcast.domain.broadcast.value_object.broadcast_id import (
    BroadcastIdVO,
)
from src.modules.broadcast.domain.broadcast.value_object.broadcast_status import (
    BroadcastStatusVO,
)


@dataclass(slots=True)
class BroadcastEntity:
    id: BroadcastIdVO

    created_at: datetime
    updated_at: datetime | None

    title: str
    description: str | None

    status: BroadcastStatusVO
