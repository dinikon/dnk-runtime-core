from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.domain.offer.value_object import OfferIdVO, OfferStateIdVO
from src.modules.price_lists.domain.sync_run.value_object import SyncRunIdVO


@dataclass(slots=True, frozen=True)
class SyncRunDTO:
    """Публичная история запусков прайса."""

    id: SyncRunIdVO
    price_list_id: PriceListIdVO
    scheduled_job_id: EntityIdVO | None
    status: str
    trigger: str
    planned_at: datetime | None
    started_at: datetime
    finished_at: datetime | None
    source_checksum: str | None
    counters: dict[str, int]
    error_summary: str | None


__all__ = ["SyncRunDTO"]
