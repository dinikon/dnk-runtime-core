from dataclasses import dataclass
from datetime import datetime
from typing import Any
from decimal import Decimal
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.domain.sync_run.value_object import SyncRunIdVO
from src.modules.price_lists.domain.offer.value_object import OfferIdVO, OfferStateIdVO


@dataclass(slots=True, frozen=True)
class ActionDTO:
    """Результат lifecycle mutation или постановки задачи."""

    id: PriceListIdVO | None = None
    status: str | None = None
    job_id: EntityIdVO | None = None
    canceled_jobs: int | None = None
    next_sync_at: datetime | None = None


@dataclass(slots=True, frozen=True)
class PreviewRowDTO:
    """Ограниченная диагностическая строка preview."""

    row_number: int
    values: dict[str, Any]
    errors: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class PreviewDTO:
    """Структура и sample источника."""

    format: str
    content_type: str
    size: int
    checksum: str
    rows: tuple[PreviewRowDTO, ...]
    sheets: tuple[str, ...] = ()
    columns: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class SchedulePreviewDTO:
    """Ближайшие occurrences расписания."""

    occurrences: tuple[datetime, ...]


__all__ = ["ActionDTO", "PreviewRowDTO", "PreviewDTO", "SchedulePreviewDTO"]
