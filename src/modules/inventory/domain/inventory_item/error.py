from src.modules.inventory.domain.error import InventoryError


class InventoryItemError(InventoryError):
    """Базовая ошибка складской номенклатуры."""


class InvalidInventoryItemValueError(InventoryItemError):
    """Сообщает о некорректных типах состояния позиции или её Entity."""


class InvalidSkuError(InventoryItemError):
    """Сообщает о недопустимом вручную заданном SKU."""


class InvalidBarcodeError(InventoryItemError):
    """Сообщает о недопустимом значении штрихкода."""


class InvalidConversionFactorError(InventoryItemError):
    """Сообщает о некорректном коэффициенте пересчёта в базовую единицу."""


class InvalidTrackingConfigurationError(InventoryItemError):
    """Сообщает о несовместимых настройках прослеживаемости и срока годности."""


class InventoryItemConflictError(InventoryItemError):
    """Сообщает о дубликатах или конфликте зависимых частей агрегата."""


class InventoryItemComponentNotFoundError(InventoryItemError):
    """Сообщает об отсутствии дочернего объекта в данной позиции."""


class UnknownUomError(InventoryItemError):
    """Сообщает о необъявленной единице содержимого упаковки товара."""


class InvalidPackagingQuantityError(InventoryItemError):
    """Сообщает о некорректном количестве содержимого упаковки."""
