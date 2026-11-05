from src.modules.inventory.domain.error import InventoryError


class StockPositionError(InventoryError):
    """Базовая ошибка физической учётной позиции."""


class InvalidStockPositionValueError(StockPositionError):
    """Сообщает о некорректном собственном состоянии позиции."""


class InvalidStockPositionSnapshotError(StockPositionError):
    """Сообщает о некорректном снимке неизменяемых атрибутов позиции."""


class InvalidStockPositionAvailabilitySnapshotError(StockPositionError):
    """Сообщает о некорректном снимке физического количества для расчёта доступности."""


class InvalidStockPositionCountingSnapshotError(StockPositionError):
    """Отклоняет неверный снимок физического количества и версии для инвентаризации."""


class InvalidStockDimensionsError(StockPositionError):
    """Сообщает о неверных типах учётных измерений."""


class StockDimensionsMismatchError(StockPositionError):
    """Сообщает о несоответствии измерений переданным снимкам."""


class InvalidStockTrackingDimensionsError(StockPositionError):
    """Сообщает о несовместимых режиме прослеживаемости, партии и серии."""


class InvalidSerialStockQuantityError(StockPositionError):
    """Требует PCS и физический остаток 0 или 1 для конкретного серийного экземпляра."""


class StockPositionUomMismatchError(StockPositionError):
    """Запрещает переинтерпретацию остатка в другой базовой единице товара."""


class StockPositionVersionConflictError(StockPositionError):
    """Отклоняет применение записи по версии, не совпадающей с текущей версией позиции."""


class StockPostingPositionMismatchError(StockPositionError):
    """Запрещает применять запись Ledger к другой физической позиции."""
