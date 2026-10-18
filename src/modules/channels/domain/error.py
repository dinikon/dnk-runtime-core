class ChannelsError(Exception):
    """Обозначает безопасный предметный отказ Channels."""


class ChannelsNotFoundError(ChannelsError):
    """Сообщает об отсутствии объекта в текущем tenant."""


class ChannelsConflictError(ChannelsError):
    """Сообщает о конфликте версии, identity или единственности."""


class ChannelsValidationError(ChannelsError):
    """Сообщает о недопустимых значениях настроек или публикации."""


class ChannelsUnavailableError(ChannelsError):
    """Сообщает о недоступности требуемой операции."""
