from src.modules.shared.domain.domain_error import DomainError


class CompanyNotFoundError(DomainError):
    """Компания не найдена в текущем tenant."""


class InvalidCompanyNameError(DomainError):
    """Название компании не соответствует доменным ограничениям."""


__all__ = ["CompanyNotFoundError", "InvalidCompanyNameError"]
