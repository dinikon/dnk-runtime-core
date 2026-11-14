from src.modules.inventory.domain.error import InventoryError


class StockLotError(InventoryError):
    """Базовая ошибка складской партии."""


class InvalidStockLotValueError(StockLotError):
    """Сообщает о некорректных типах собственного состояния партии."""


class InvalidLotNumberError(StockLotError):
    """Сообщает о некорректном номере партии."""


class LotTrackingNotAllowedError(StockLotError):
    """Запрещает использование партии для товара без партийного учёта."""


class StockLotItemMismatchError(StockLotError):
    """Сообщает, что партия и снимок относятся к разным товарам."""


class InvalidStockLotSnapshotError(StockLotError):
    """Сообщает о некорректном снимке идентичности и дат партии."""


class StockLotNotFoundError(StockLotError):
    """Сообщает об отсутствующей партии в выбранном SKU."""


class StockLotNumberAlreadyExistsError(StockLotError):
    """Сообщает о занятом точном номере партии внутри SKU текущего tenant."""
