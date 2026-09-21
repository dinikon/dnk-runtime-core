from src.modules.currency.application.provider.catalog import (
    RateSourceCatalog,
    RateSourceDTO,
)
from src.modules.currency.application.provider.query.list_rate_sources_query import (
    ListRateSourcesQuery,
)


class ListRateSourcesUseCase:
    """Describe registered adapters without making external calls."""

    def __init__(self, catalog: RateSourceCatalog):
        self.catalog = catalog

    async def __call__(self, query: ListRateSourcesQuery) -> tuple[RateSourceDTO, ...]:
        return self.catalog.list()


__all__ = ["ListRateSourcesUseCase"]
