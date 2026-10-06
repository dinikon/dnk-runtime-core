from dataclasses import dataclass


class ChannelConfigConflictError(Exception):
    """Сообщает о несовпадении версии формы с опубликованной конфигурацией."""


class ChannelSecretsUnavailableError(Exception):
    """Сообщает о недоступности защищённого хранилища без раскрытия ключей."""


@dataclass(frozen=True, slots=True)
class ChannelFieldError:
    """Описывает ошибку поля без входного значения и HTTP-представления."""

    path: tuple[str | int, ...]
    message: str
    code: str


class ChannelValidationError(Exception):
    """Передаёт безопасные ошибки проверки настроек к транспортной границе."""

    def __init__(self, errors: tuple[ChannelFieldError, ...]) -> None:
        """Сохраняет только пути полей, безопасные сообщения и коды ошибок."""
        super().__init__("Invalid channel settings.")
        self.errors = errors
