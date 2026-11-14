from src.modules.shared.domain.domain_error import DomainError


class InvalidContactNameError(DomainError):
    """Имя контакта нарушает правила полноты, типа или длины."""


class ContactNotFoundError(DomainError):
    """Контакт отсутствует в текущем tenant."""


class InvalidContactCompanyLinkError(DomainError):
    """Пара идентификаторов связи Contact–Company имеет неверные типы."""


class ContactInUseError(DomainError):
    """Контакт используется источниками поставки и не может быть удалён."""
