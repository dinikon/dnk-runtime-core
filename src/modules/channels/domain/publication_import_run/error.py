from src.modules.shared.domain.domain_error import DomainError


class InvalidPublicationImportError(DomainError):
    """Нарушен жизненный цикл импорта публикаций."""


class PublicationImportNotFoundError(DomainError):
    """Импорт не найден в текущем канале."""
