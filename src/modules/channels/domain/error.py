class ChannelError(Exception):
    """Безопасная предметная ошибка Channels."""


class InvalidChannelError(ChannelError):
    pass


class ChannelNotFoundError(ChannelError):
    pass


class ChannelConfigConflictError(ChannelError):
    pass


class ChannelSecretsUnavailableError(ChannelError):
    pass


class ChannelValidationError(InvalidChannelError):
    def __init__(self, errors: tuple[dict, ...]):
        super().__init__("Invalid channel settings.")
        self.errors = errors
