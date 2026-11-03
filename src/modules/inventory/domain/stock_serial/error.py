from src.modules.inventory.domain.error import InventoryError


class StockSerialError(InventoryError):
    """Базовая ошибка серийного экземпляра товара."""


class InvalidStockSerialValueError(StockSerialError):
    """Сообщает о некорректных типах собственного состояния экземпляра."""


class InvalidSerialNumberError(StockSerialError):
    """Сообщает о некорректном серийном номере."""


class InvalidSerialConfigurationError(StockSerialError):
    """Сообщает о несовместимых источнике дат, партии или режиме экземпляра."""


class SerialTrackingNotAllowedError(StockSerialError):
    """Запрещает серийный экземпляр для товара без серийного учёта."""


class StockSerialItemMismatchError(StockSerialError):
    """Сообщает, что экземпляр и снимок относятся к разным товарам."""


class StockSerialLotMismatchError(StockSerialError):
    """Сообщает о другой партии или товаре в снимке связанной партии."""
