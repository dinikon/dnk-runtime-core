from typing import Protocol
from src.modules.inventory.application.stock_document.query.get_return_origin.query import (
    GetReturnOriginQuery,
)
from src.modules.inventory.application.stock_document.query.get_return_origin.dto import (
    GetReturnOriginResultDTO,
)


class ReturnOriginQueryPort(Protocol):
    """Читает конкретную проекцию исходного факта и накопленных возвратов."""

    async def get(
        self, query: GetReturnOriginQuery, *, direction: str
    ) -> GetReturnOriginResultDTO | None:
        """Возвращает строки с точным остатком к возврату."""
        ...
