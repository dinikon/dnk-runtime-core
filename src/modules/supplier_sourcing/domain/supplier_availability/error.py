from src.modules.supplier_sourcing.domain.error import SupplierSourcingError


class SupplierAvailabilityError(SupplierSourcingError):
    """Базовая ошибка учёта наблюдений внешнего наличия."""


class InvalidSupplierAvailabilityValueError(SupplierAvailabilityError):
    """Отклоняет некорректные поля агрегата или несовместимые значения наблюдения."""


class SupplierAvailabilityContextMismatchError(SupplierAvailabilityError):
    """Отклоняет несовместимое предложение, источник или единицу наблюдения."""


class SupplierAvailabilityVersionConflictError(SupplierAvailabilityError):
    """Отклоняет обновление по устаревшей версии наблюдения."""


class SupplierAvailabilityTimeError(SupplierAvailabilityError):
    """Отклоняет некорректное время, срок действия или порядок наблюдений."""
