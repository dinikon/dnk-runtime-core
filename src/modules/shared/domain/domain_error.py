class DomainError(Exception):
    """Базовая доменная ошибка всего проекта."""


class EntityIdTypeError(DomainError):
    """Ошибка некорректного типа значения EntityIdVO."""

    pass
