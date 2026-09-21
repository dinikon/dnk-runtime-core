from typing import Protocol
from src.modules.currency.application.provider.dto.provider_status_dto import (
    ProviderStatusDTO,
)
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode


class ProviderStatusQueryRepository(Protocol):
    """Global import status read model, independent from tenant rate resolution."""

    async def provider_status(self, provider: ProviderCode) -> ProviderStatusDTO: ...


__all__ = ["ProviderStatusQueryRepository"]
