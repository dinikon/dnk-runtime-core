from src.modules.feed_builder.domain.error import FeedBuilderDomainError


class FeedDomainError(FeedBuilderDomainError):
    """Описывает нарушение определения Feed с путём к проблемному значению."""


class InvalidFeedValueError(FeedDomainError):
    """Сообщает о некорректном собственном значении VO или агрегата."""


class FeedNotFoundError(FeedDomainError):
    """Сообщает об отсутствии Feed в текущем tenant."""


class FeedCodeConflictError(FeedDomainError):
    """Сообщает о занятом коде Feed, включая архивные записи."""


class FeedVersionConflictError(FeedDomainError):
    """Отклоняет сохранение устаревшей версии Feed."""


class FeedArchivedError(FeedDomainError):
    """Запрещает изменение настроек архивного Feed."""


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
