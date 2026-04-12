from src.modules.shared import DomainError


class RuntimeDataError(DomainError):
    """Базовая доменная ошибка модуля runtime_data."""

    pass


class RuntimeDataValidationError(RuntimeDataError):
    """Ошибка пользовательских данных, не прошедших runtime-валидацию."""

    pass


class RuntimeDataObjectNotFoundError(RuntimeDataError):
    """Ошибка отсутствия runtime-записи объекта."""

    pass


class RuntimeDataFilterError(RuntimeDataError):
    """Ошибка некорректного фильтра или сортировки runtime-запроса."""

    pass


class RuntimeDataPolicyError(RuntimeDataError):
    """Ошибка нарушения runtime-политики типов или descriptor."""

    pass


class RuntimeDataPersistenceError(RuntimeDataError):
    """Ошибка сохранения или чтения runtime-данных в backend-хранилище."""

    pass
