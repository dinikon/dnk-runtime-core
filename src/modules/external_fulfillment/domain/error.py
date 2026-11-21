from src.modules.shared.domain.domain_error import DomainError


class SupplierFulfillmentError(DomainError):
    """Базовая ошибка прямого исполнения поставщиком."""


class InvalidSupplierFulfillmentValueError(SupplierFulfillmentError):
    """Отклоняет некорректные значения заказа, строки или снимка."""


class SupplierFulfillmentBasisMismatchError(SupplierFulfillmentError):
    """Отклоняет несовместимое основание плана, источника или предложения."""


class SupplierFulfillmentTimeError(SupplierFulfillmentError):
    """Отклоняет некорректную хронологию внешнего заказа."""


class SupplierFulfillmentVersionConflictError(SupplierFulfillmentError):
    """Отклоняет изменение по устаревшей версии внешнего заказа."""


class SupplierFulfillmentStatusError(SupplierFulfillmentError):
    """Отклоняет действие, несовместимое с состоянием внешнего заказа."""
