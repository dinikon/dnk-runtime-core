from typing import Protocol

from src.modules.inventory.domain.stock_location.aggregate import StockLocation
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class StockLocationRepositoryProtocol(Protocol):
    """Определяет чтение и запись самостоятельной локации в общей транзакции."""

    async def get(self, identifier: StockLocationIdVO) -> StockLocation | None:
        """Возвращает актуальный агрегат родительской локации либо None."""
        ...

    async def add(self, location: StockLocation) -> None:
        """Сохраняет новую локацию без самостоятельного commit."""
        ...

    async def get_for_update(
        self, identifier: StockLocationIdVO, *, warehouse_id: WarehouseIdVO
    ) -> StockLocation | None:
        """Блокирует актуальную локацию только внутри указанного склада."""
        ...

    async def save(self, location: StockLocation) -> None:
        """Обновляет редактируемые поля существующего адреса без upsert и commit."""
        ...
