from src.modules.price_lists.application.price_list.query.preview_price_list_query import (
    PreviewPriceListQuery,
)


class PreviewPriceListUseCase:
    """Выполняет запрос preview_price_list."""

    def __init__(self, repository, preview):
        self.repository = repository
        self.preview = preview

    async def __call__(self, query: PreviewPriceListQuery):
        """Выполняет сценарий через внедрённые доменные порты."""
        price = await self.repository.get(query.tenant_id, query.price_list_id)
        return await self.preview.inspect(
            self.preview.candidate(price, query.candidate), limit=query.limit
        )


__all__ = ["PreviewPriceListUseCase"]
