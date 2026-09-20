from src.modules.price_lists.application.price_list.query.list_price_lists_query import (
    ListPriceListsQuery,
)
from src.modules.price_lists.application.price_list.dto.price_list_dto import (
    price_list_dto,
)
from src.modules.price_lists.application.price_list.dto.action_dto import (
    SchedulePreviewDTO,
)


class ListPriceListsUseCase:
    """Выполняет запрос list_price_lists."""

    def __init__(self, repository):
        self.repository = repository

    async def __call__(self, query: ListPriceListsQuery):
        return await self.repository.list(query.tenant_id, scope=query.scope)


__all__ = ["ListPriceListsUseCase"]
