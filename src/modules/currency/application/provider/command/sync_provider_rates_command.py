from dataclasses import dataclass
from datetime import date
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.domain.rate_import.value_object.id import RateImportIdVO


@dataclass(frozen=True, slots=True)
class SyncProviderRatesCommand:
    """Immutable input for sync provider rates."""

    id: RateImportIdVO
    provider: ProviderCode
    start_date: date
    end_date: date


__all__ = ["SyncProviderRatesCommand"]
