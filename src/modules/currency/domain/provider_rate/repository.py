from typing import Protocol
from src.modules.currency.domain.exchange_rate.repository import RateRepository


class ProviderRateRepository(RateRepository, Protocol):
    """Read locally stored provider revisions, explicitly scoped by caller tenant."""


__all__ = ["ProviderRateRepository"]
