from typing import Protocol

from src.modules.inventory.domain.stock_serial.aggregate import StockSerial


class StockSerialRepositoryProtocol(Protocol):
    """Определяет запись самостоятельного экземпляра в общей tenant-транзакции."""

    async def add(self, serial: StockSerial) -> None:
        """Добавляет экземпляр без commit либо сообщает о занятом номере внутри SKU."""
        ...
