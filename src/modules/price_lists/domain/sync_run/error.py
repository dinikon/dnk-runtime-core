from src.modules.shared.domain.domain_error import DomainError


class SourceValidationError(DomainError):
    """Импорт не прошёл итоговую проверку источника."""


class DuplicateExternalIdError(SourceValidationError):
    """Источник содержит повторяющиеся external_id."""


class SyncRunNotFoundError(DomainError):
    """Запуск синхронизации не найден."""


class LostJobLease(RuntimeError):
    """Задача утратила право изменять данные."""


__all__ = [
    "SourceValidationError",
    "DuplicateExternalIdError",
    "SyncRunNotFoundError",
    "LostJobLease",
]
