from dataclasses import dataclass
from src.modules.currency.application.exchange_rate.dto.rate_record_dto import (
    RateRecordDTO,
)


@dataclass(frozen=True, slots=True)
class SetManualRateResult:
    """Saved manual revision and whether this call created it."""

    rate: RateRecordDTO
    created: bool


__all__ = ["SetManualRateResult"]
