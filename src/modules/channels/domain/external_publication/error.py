from src.modules.shared.domain.domain_error import DomainError


class InvalidPublicationError(DomainError):
    """Нарушены инварианты сохранённой публикации."""


class PublicationNotFoundError(DomainError):
    """Публикация отсутствует в текущем подключении канала."""
