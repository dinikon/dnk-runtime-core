from src.modules.shared.domain.domain_error import DomainError


class InventoryItemError(DomainError):
    """Базовая ошибка складской номенклатуры."""


class InvalidInventoryItemValueError(InventoryItemError):
    """Сообщает о некорректных типах состояния позиции или её Entity."""


class InvalidSkuError(InventoryItemError):
    """Сообщает о недопустимом вручную заданном SKU."""


class InvalidUomCodeError(InventoryItemError):
    """Сообщает о недопустимом коде единицы учёта."""


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
    """Сообщает о ссылке штрихкода на необъявленную единицу учёта."""
