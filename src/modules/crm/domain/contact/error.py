from src.modules.shared.domain.domain_error import DomainError


class ContactNotFoundError(DomainError):
    """Контакт не найден в текущем tenant."""


class InvalidContactNameError(DomainError):
    """ФИО контакта не соответствует доменным ограничениям."""


__all__ = ["ContactNotFoundError", "InvalidContactNameError"]
