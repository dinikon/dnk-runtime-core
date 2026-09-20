from src.modules.price_lists.application.price_list.query.get_price_list_query import (
    GetPriceListQuery,
)
from src.modules.price_lists.application.price_list.dto.price_list_dto import (
    price_list_dto,
)
from src.modules.price_lists.application.price_list.dto.action_dto import (
    SchedulePreviewDTO,
)


class GetPriceListUseCase:
    """Выполняет запрос get_price_list."""

    def __init__(self, repository):
        self.repository = repository

    async def __call__(self, query: GetPriceListQuery):
        return price_list_dto(
            await self.repository.get(query.tenant_id, query.price_list_id)
        )


__all__ = ["GetPriceListUseCase"]
