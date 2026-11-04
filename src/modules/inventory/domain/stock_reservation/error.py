from src.modules.inventory.domain.error import InventoryError


class StockReservationError(InventoryError):
    """Базовая ошибка мягкого резерва под конкретное обязательство."""


class InvalidStockReservationValueError(StockReservationError):
    """Сообщает о некорректном собственном составе или версии резерва."""


class InvalidReservationSourceError(StockReservationError):
    """Сообщает о некорректной системе или ссылке строки обязательства."""


class InvalidStockReservationQuantityError(StockReservationError):
    """Требует положительное запрошенное или изменяемое количество резерва."""


class StockReservationLimitExceededError(StockReservationError):
    """Запрещает сумме текущего удержания и погашения превышать неизменяемый запрос."""


class StockReservationReleaseExceededError(StockReservationError):
    """Запрещает освобождать больше удерживаемого данным обязательством количества."""


class StockReservationConsumptionExceededError(StockReservationError):
    """Запрещает погашать больше текущего удержания данного обязательства."""


class StockReservationStatusError(StockReservationError):
    """Сообщает о несовместимом статусе или попытке изменить терминальное состояние."""


class StockReservationTimeError(StockReservationError):
    """Требует время с часовым поясом и согласованную UTC-хронологию резерва."""


class StockReservationExpiredError(StockReservationError):
    """Запрещает новое удержание или факт использования с момента окончания срока резерва."""


class StockReservationExpirationError(StockReservationError):
    """Запрещает явное истечение без срока или до его наступления."""


class StockReservationVersionConflictError(StockReservationError):
    """Отклоняет переход по версии, отличной от текущей версии обязательства."""


class StockReservationItemMismatchError(StockReservationError):
    """Запрещает использовать настройки другого товара для данного обязательства."""


class StockReservationUomMismatchError(StockReservationError):
    """Запрещает переинтерпретацию запрошенного и удерживаемого количества в другой единице."""
