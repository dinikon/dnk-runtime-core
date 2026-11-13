from src.modules.inventory.domain.error import InventoryError


class StockLocationError(InventoryError):
    """Базовая ошибка адреса хранения."""


class StockLocationNotFoundError(StockLocationError):
    """Сообщает об отсутствии запрошенной локации в текущем контексте."""


class StockLocationCodeAlreadyExistsError(StockLocationError):
    """Сообщает о занятом каноническом коде локации внутри склада."""


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
