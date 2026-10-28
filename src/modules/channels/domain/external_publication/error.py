"""Ошибки наблюдаемого состояния внешней публикации."""

from src.modules.shared.domain.domain_error import DomainError


class ExternalPublicationError(DomainError):
    """Базовая ошибка публикаций."""


class InvalidExternalPublicationError(ExternalPublicationError):
    """Снимок либо связь публикации противоречит правилам модели."""


class ExternalPublicationNotFoundError(ExternalPublicationError):
    """Публикация отсутствует в выбранном подключении."""
