from src.modules.feed_builder.domain.error import FeedBuilderDomainError


class GenerationDomainError(FeedBuilderDomainError):
    """Описывает нарушение модели отдельной сборки выгрузки."""


class InvalidGenerationValueError(GenerationDomainError):
    """Отклоняет некорректное значение или несогласованное состояние генерации."""
