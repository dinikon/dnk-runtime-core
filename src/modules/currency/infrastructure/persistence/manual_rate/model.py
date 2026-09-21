from __future__ import annotations
from src.modules.currency.infrastructure.persistence.schema import rate_table
from src.modules.shared.infrastructure.persistence import TenantBase


class ManualExchangeRateModel(TenantBase):
    """Persistence mapping for manual exchange rate."""

    __table__ = rate_table("manual_exchange_rate", TenantBase.metadata, provider=False)


__all__ = ["ManualExchangeRateModel"]
