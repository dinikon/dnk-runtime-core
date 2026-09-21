from src.modules.currency.application.provider.dto.provider_status_dto import (
    ProviderStatusDTO,
)
from src.modules.currency.application.provider.query.get_provider_status_query import (
    GetProviderStatusQuery,
)
from src.modules.currency.application.provider.query.repository import (
    ProviderStatusQueryRepository,
)


class GetProviderStatusUseCase:
    """Execute the get provider status read scenario."""

    def __init__(self, repository: ProviderStatusQueryRepository):
        self.repository = repository

    async def __call__(self, query: GetProviderStatusQuery) -> ProviderStatusDTO:
        return await self.repository.provider_status(query.provider)


__all__ = ["GetProviderStatusUseCase"]
