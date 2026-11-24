from src.modules.feed_builder.domain.error import FeedBuilderDomainError


class InvalidExportStateError(FeedBuilderDomainError):
    """Отклоняет несогласованное состояние экспорта."""
