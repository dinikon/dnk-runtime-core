from dataclasses import dataclass
from datetime import date
from src.modules.currency.application.conversion.error import UNAVAILABLE_CONVERSION


@dataclass(frozen=True, slots=True)
class UnavailableConversion:
    """Expected business failure, never an infrastructure exception."""

    code: str
    message: str
    business_date: date

    def raise_error(self) -> None:
        """Restore the specific business error for a single-item facade call."""
        for error_type in UNAVAILABLE_CONVERSION:
            if error_type.code == self.code:
                raise error_type(self.message)
        from src.modules.currency.domain.exchange_rate.error import CrossRateUnavailable

        if self.code == CrossRateUnavailable.code:
            raise CrossRateUnavailable(self.message)
        raise RuntimeError(f"Unknown conversion failure: {self.code}")


__all__ = ["UnavailableConversion"]
