from src.modules.inventory.domain.error import InventoryError


class WarehouseError(InventoryError):
    """Базовая ошибка складского справочника."""


class InvalidWarehouseValueError(WarehouseError):
    """Сообщает о некорректных типах собственного состояния склада."""


class InvalidWarehouseCodeError(WarehouseError):
    """Сообщает о некорректном пользовательском коде склада."""


class InvalidWarehouseNameError(WarehouseError):
    """Сообщает о некорректном названии склада."""


class WarehouseInactiveError(WarehouseError):
    """Запрещает использование административно неактивного склада."""
