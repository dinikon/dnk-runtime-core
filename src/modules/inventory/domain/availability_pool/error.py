from src.modules.inventory.domain.error import InventoryError


class AvailabilityPoolError(InventoryError):
    """Базовая ошибка общего пула пригодного запаса и действующих резервов."""


class InvalidAvailabilityPoolKeyError(AvailabilityPoolError):
    """Сообщает о некорректном ключе товара, склада и владельца."""


class InvalidAvailabilityPoolValueError(AvailabilityPoolError):
    """Сообщает о некорректном собственном составе пула."""


class InvalidAvailabilityPoolReservationSnapshotError(AvailabilityPoolError):
    """Сообщает о некорректном снимке привязки обязательства к пулу."""


class AvailabilityPoolContextMismatchError(AvailabilityPoolError):
    """Запрещает использовать снимки другого товара или склада для данного пула."""


class AvailabilityPoolUomMismatchError(AvailabilityPoolError):
    """Запрещает переинтерпретацию количеств пула в новой базовой единице товара."""


class AvailabilityPoolVersionConflictError(AvailabilityPoolError):
    """Отклоняет изменение по версии, отличной от текущей версии пула."""


class AvailabilityAssessmentDateError(AvailabilityPoolError):
    """Запрещает некалендарную дату или пересчёт раньше сохранённого дня оценки."""


class InvalidReservationQuantityError(AvailabilityPoolError):
    """Требует строго положительное количество резервирования или освобождения."""


class InsufficientAvailableStockError(AvailabilityPoolError):
    """Запрещает новый резерв сверх пригодного запаса за вычетом действующих резервов."""


class ExcessiveReservationReleaseError(AvailabilityPoolError):
    """Запрещает освобождать количество сверх общего действующего резерва."""


class ExcessiveReservationConsumptionError(AvailabilityPoolError):
    """Запрещает погашать количество сверх общего действующего резерва."""


class InvalidPoolReservationConsumptionsError(AvailabilityPoolError):
    """Запрещает пустой, повторный или смешивающий исполнения набор погашений пула."""


class AvailabilityPoolConsumptionMismatchError(AvailabilityPoolError):
    """Запрещает погашения, предназначенные другому пулу или области учёта."""
