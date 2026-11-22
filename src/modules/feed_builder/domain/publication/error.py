from src.modules.feed_builder.domain.error import FeedBuilderDomainError


class PublicationDomainError(FeedBuilderDomainError):
    """Описывает нарушение модели выбранной товарной позиции."""


class InvalidPublicationValueError(PublicationDomainError):
    """Отклоняет некорректное значение или состояние публикации."""


class DuplicateFieldOverrideError(PublicationDomainError):
    """Отклоняет несколько ручных значений одного поля публикации."""


class PublicationNotFoundError(PublicationDomainError):
    """Сообщает об отсутствующей публикации текущего tenant."""


class PublicationVersionConflictError(PublicationDomainError):
    """Отклоняет устаревшую версию публикации."""


class PublicationTransitionError(PublicationDomainError):
    """Отклоняет недопустимый переход участия."""


class InvalidPublicationOverrideError(InvalidPublicationValueError):
    """Передаёт адресованную ошибку проверки ручного значения."""

    def __init__(self, code: str, message: str) -> None:
        """Сохраняет код и ошибку поля value."""
        super().__init__(message, path=("value",))
        self.code = code
