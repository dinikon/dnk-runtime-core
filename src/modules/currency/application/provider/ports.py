from __future__ import annotations
from datetime import date
from typing import Protocol
from typing import Sequence
from src.modules.currency.application.provider.dto.provider_capabilities import (
    ProviderCapabilities,
)
from src.modules.currency.application.provider.dto.provider_rate_dto import (
    ProviderRateDTO,
)
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode


class ExchangeRateProviderPort(Protocol):
    """External batch fetch contract, excluded from ordinary conversion."""

    code: ProviderCode
    capabilities: ProviderCapabilities

    async def fetch(
        self, *, start_date: date, end_date: date
    ) -> Sequence[ProviderRateDTO]: ...


__all__ = ["ExchangeRateProviderPort"]
