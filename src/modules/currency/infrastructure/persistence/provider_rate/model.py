from __future__ import annotations
from src.modules.currency.infrastructure.persistence.schema import rate_table
from src.modules.shared.infrastructure.persistence import Base


class ProviderRateModel(Base):
    """Persistence mapping for provider rate."""

    __table__ = rate_table("fx_provider_rate", Base.metadata, provider=True)


__all__ = ["ProviderRateModel"]
