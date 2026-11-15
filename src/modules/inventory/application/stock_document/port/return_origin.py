from typing import Protocol
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.return_origin_snapshot import (
    StockReturnOriginSnapshot,
    StockReturnUsageSnapshot,
)


class ReturnOriginPort(Protocol):
    """Читает бизнес-основание и сериализует конкурирующие возвраты на исходном корне."""

    async def get(
        self, identifier: StockExecutionIdVO, *, lock: bool
    ) -> StockReturnOriginSnapshot | None:
        """Возвращает полный снимок проведённого основания, при необходимости блокируя его корень."""
        ...

    async def usage(
        self, identifier: StockExecutionIdVO
    ) -> tuple[StockReturnUsageSnapshot, ...]:
        """Суммирует только фактические возвраты всех документов по каждой исходной строке."""
        ...
