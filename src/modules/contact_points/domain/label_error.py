from src.modules.shared.domain.domain_error import DomainError


class ContactPointLabelNotFoundError(DomainError):
    """Подпись отсутствует в tenant."""


class InvalidContactPointLabelError(DomainError):
    """Некорректные параметры подписи."""


__all__ = ["ContactPointLabelNotFoundError", "InvalidContactPointLabelError"]
