from src.modules.shared.domain.domain_error import DomainError


class InvalidAttributeError(DomainError):
    """Недопустимый код, перевод или набор вариантов атрибута."""


class AttributeAlreadyExistsError(DomainError):
    """Код атрибута занят в текущем tenant."""


class AttributeNotFoundError(DomainError):
    """Атрибут не найден в текущем tenant."""


class InvalidAttributeLocaleError(DomainError):
    """Код локали перевода атрибута имеет неверный формат."""


class AttributeLocaleUnavailableError(DomainError):
    """Локаль перевода атрибута не активна в глобальном справочнике."""
