from src.modules.feed_builder.domain.error import FeedBuilderDomainError


class AccessKeyDomainError(FeedBuilderDomainError):
    """Описывает нарушение модели ключа публичной выгрузки."""


class InvalidAccessKeyValueError(AccessKeyDomainError):
    """Отклоняет некорректное значение или состояние ключа доступа."""
