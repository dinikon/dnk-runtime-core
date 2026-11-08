from src.modules.supplier_sourcing.domain.error import SupplierSourcingError


class SupplierSourceError(SupplierSourcingError):
    """Базовая ошибка карточки источника поставки."""


class InvalidSupplierSourceValueError(SupplierSourceError):
    """Отклоняет некорректное значение карточки источника."""


class InvalidSupplierStockUpdatePolicyError(SupplierSourceError):
    """Отклоняет некорректные настройки актуальности наличия."""


class SupplierSourceInactiveError(SupplierSourceError):
    """Запрещает выбор административно неактивного источника."""


class UnsupportedSupplierFulfillmentModeError(SupplierSourceError):
    """Сообщает, что источник не поддерживает выбранный режим поставки."""
