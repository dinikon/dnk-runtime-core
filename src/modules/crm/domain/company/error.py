from src.modules.shared.domain.domain_error import DomainError


class InvalidCompanyLegalNameError(DomainError):
    """Юридическое название компании имеет неверный тип или длину."""


class CompanyNotFoundError(DomainError):
    """Компания отсутствует в текущем tenant."""
