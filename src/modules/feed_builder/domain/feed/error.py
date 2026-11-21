from src.modules.feed_builder.domain.error import FeedBuilderDomainError


class FeedDomainError(FeedBuilderDomainError):
    """Описывает нарушение определения Feed с путём к проблемному значению."""


class InvalidFeedValueError(FeedDomainError):
    """Сообщает о некорректном собственном значении VO или агрегата."""


class InvalidFieldDefinitionError(FeedDomainError):
    """Сообщает о несовместимых настройках определения поля."""


class InvalidPriceCalculationDefinitionError(FeedDomainError):
    """Сообщает о некорректной структуре расчёта денежного поля."""


class DuplicateFieldIdentifierError(FeedDomainError):
    """Сообщает о повторном field_id внутри Feed."""


class DuplicateFieldKeyError(FeedDomainError):
    """Сообщает о повторном внутреннем ключе поля."""


class DuplicateExportNameError(FeedDomainError):
    """Сообщает о повторном экспортном имени поля."""


class DuplicatePriceRuleIdentifierError(FeedDomainError):
    """Сообщает о повторном rule_id в одном денежном расчёте."""


class DefinitionStructureLimitExceededError(FeedDomainError):
    """Отклоняет определение, превысившее структурный бюджет."""
