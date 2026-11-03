from src.modules.inventory.domain.error import InventoryError


class StockLocationError(InventoryError):
    """Базовая ошибка адреса хранения."""


class InvalidStockLocationValueError(StockLocationError):
    """Сообщает о некорректных типах собственного состояния локации."""


class InvalidLocationCodeError(StockLocationError):
    """Сообщает о некорректном коде локации."""


class InvalidLocationNameError(StockLocationError):
    """Сообщает о некорректном названии локации."""


class InvalidLocationHierarchyError(StockLocationError):
    """Запрещает прямую самоссылку в иерархии локаций."""


class InvalidStockLocationSnapshotError(StockLocationError):
    """Сообщает о некорректном снимке идентичности и назначения локации."""


class StockLocationWarehouseMismatchError(StockLocationError):
    """Сообщает о принадлежности локации другому складу."""


class StockLocationInactiveError(StockLocationError):
    """Запрещает использование неактивной локации."""
