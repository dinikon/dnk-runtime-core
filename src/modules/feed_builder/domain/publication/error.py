from src.modules.feed_builder.domain.error import FeedBuilderDomainError


class PublicationDomainError(FeedBuilderDomainError):
    """Описывает нарушение модели выбранной товарной позиции."""


class InvalidPublicationValueError(PublicationDomainError):
    """Отклоняет некорректное значение или состояние публикации."""


class DuplicateFieldOverrideError(PublicationDomainError):
    """Отклоняет несколько ручных значений одного поля публикации."""
