from dataclasses import dataclass
from datetime import date, datetime
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.domain.rate_import.value_object.id import RateImportIdVO


@dataclass(frozen=True, slots=True)
class RateImport:
    """Global provider attempt and its committed publication or failure result."""

    id: RateImportIdVO
    provider_code: ProviderCode
    started_at: datetime
    finished_at: datetime | None
    requested_date_from: date
    requested_date_to: date
    status: str
    received_count: int
    created_count: int
    updated_count: int
    error_count: int
    error_message: str | None


__all__ = ["RateImport"]
