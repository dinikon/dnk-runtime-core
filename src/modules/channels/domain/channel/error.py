"""Предметные ошибки канала без HTTP-полей и деталей внешних API."""

from src.modules.shared.domain.domain_error import DomainError


class ChannelError(DomainError):
    """Базовый отказ доменной операции канала."""


class InvalidChannelNameError(ChannelError):
    """Название пустое либо превышает допустимую длину."""


class InvalidChannelStateError(ChannelError):
    """Состояние канала или подключения противоречит его инвариантам."""


class InvalidResourceIdentityError(ChannelError):
    """Магазин не имеет поддерживаемого устойчивого идентификатора."""


class ChannelRevisionConflictError(ChannelError):
    """Операция основана на устаревшей ревизии канала."""


class ChannelNotFoundError(ChannelError):
    """Запрошенный канал отсутствует в текущем tenant."""
