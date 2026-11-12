from src.modules.inventory.domain.error import InventoryError


class WarehouseError(InventoryError):
    """Базовая ошибка складского справочника."""


class WarehouseCodeAlreadyExistsError(WarehouseError):
    """Сообщает о занятом каноническом коде склада в текущем tenant."""


class WarehouseNotFoundError(WarehouseError):
    """Сообщает об отсутствии склада в текущем tenant."""


class InvalidWarehouseValueError(WarehouseError):
    """Сообщает о некорректных типах собственного состояния склада."""


class InvalidWarehouseCodeError(WarehouseError):
    """Сообщает о некорректном пользовательском коде склада."""


class InvalidWarehouseNameError(WarehouseError):
    """Сообщает о некорректном названии склада."""


class WarehouseInactiveError(WarehouseError):
    """Запрещает использование административно неактивного склада."""


class InvalidWarehouseSnapshotError(WarehouseError):
    """Сообщает о некорректном снимке склада и основной локации."""


class InvalidDefaultStorageLocationError(WarehouseError):
    """Запрещает назначение локации другого назначения в качестве основной STORAGE."""


class DefaultStorageLocationInUseError(WarehouseError):
    """Требует переназначить основную локацию перед её деактивацией."""
