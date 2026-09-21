from dataclasses import dataclass
from datetime import datetime
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO


@dataclass(slots=True)
class EnabledCurrency:
    """Tenant permission to use a currency in a new operation."""

    currency: CurrencyCodeVO
    enabled: bool
    created_at: datetime
    updated_at: datetime

    def update(self, enabled: bool, now: datetime) -> bool:
        if self.enabled == enabled:
            return False
        self.enabled, self.updated_at = enabled, now
        return True


__all__ = ["EnabledCurrency"]
