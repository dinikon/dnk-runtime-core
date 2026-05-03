from src.modules.shared import DomainError


class CustomObjectError(DomainError):
    """Базовая ошибка модуля custom_object."""

    pass


class CustomObjectNotFoundError(CustomObjectError):
    """Ошибка отсутствия кастомного объекта в tenant scope."""

    pass


class CustomObjectFieldNotFoundError(CustomObjectError):
    """Ошибка отсутствия поля кастомного объекта."""

    pass


class CustomObjectRecordNotFoundError(CustomObjectError):
    """Ошибка отсутствия записи кастомного объекта."""

    pass


class CustomObjectValidationError(CustomObjectError):
    """Ошибка пользовательского payload или запрещенной custom-object операции."""

    pass
