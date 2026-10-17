from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RefreshExchangeRatesResultDTO:
    """Возвращает метаданные опубликованной проверки и диагностические счётчики."""

    source: str
    snapshot_id: UUID
    quote_count: int
    effective_date: date
    checked_at: datetime
    excluded_unknown_count: int
    excluded_metal_count: int
