from src.modules.shared.domain.domain_error import DomainError


class SupplierSourcingError(DomainError):
    """Базовая ошибка домена источников и предложений поставщиков."""


class InvalidSupplierLeadTimeError(SupplierSourcingError):
    """Требует неотрицательную длительность поставки."""
