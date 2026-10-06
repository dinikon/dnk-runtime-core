class ChannelError(Exception):
    """Базовая безопасная ошибка предметной области Channels."""


class InvalidChannelError(ChannelError):
    """Сообщает о нарушении инварианта с безопасным именем предметного поля."""

    def __init__(self, message: str, *, field_name: str | None = None) -> None:
        """Сохраняет описание правила и имя поля без входного значения."""
        super().__init__(message)
        self.field_name = field_name


class ChannelNotFoundError(ChannelError):
    """Сообщает об отсутствии запрошенного канала или платформы."""
