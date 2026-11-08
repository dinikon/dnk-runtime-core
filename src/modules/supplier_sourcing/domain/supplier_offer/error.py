from src.modules.supplier_sourcing.domain.error import SupplierSourcingError


class SupplierOfferError(SupplierSourcingError):
    """Базовая ошибка коммерческого предложения поставщика."""


class InvalidSupplierOfferValueError(SupplierOfferError):
    """Отклоняет некорректные поля предложения или его снимков."""


class SupplierOfferSourceMismatchError(SupplierOfferError):
    """Отклоняет источник, принадлежащий другому поставщику."""


class SupplierOfferInactiveError(SupplierOfferError):
    """Запрещает заказ по неактивному предложению."""


class SupplierOrderQuantityError(SupplierOfferError):
    """Отклоняет количество, единицу или нарушение коммерческих условий заказа."""
