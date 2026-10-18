from collections.abc import Mapping
from typing import Any
from src.modules.channels.application.channel.query.get_channel.dto import (
    GetChannelResultDTO,
)
from src.modules.channels.application.channel.query.list_channels.dto import (
    ListChannelsItemDTO,
)
from src.modules.channels.application.channel.query.get_connection.dto import (
    GetConnectionResultDTO,
)


class ChannelQueryMapper:
    """Собирает DTO чтения без восстановления Channel/Connection."""

    @staticmethod
    def to_details(row: Mapping[str, Any]) -> GetChannelResultDTO:
        """Возвращает детали одного канала."""
        return GetChannelResultDTO(**dict(row))

    @staticmethod
    def to_list_item(row: Mapping[str, Any]) -> ListChannelsItemDTO:
        """Возвращает строку списка каналов."""
        return ListChannelsItemDTO(**dict(row))

    @staticmethod
    def to_connection(row: Mapping[str, Any]) -> GetConnectionResultDTO:
        """Исключает ciphertext из проекции технических настроек."""
        values = dict(row)
        values["locales"] = tuple(values["locales"])
        values["scope_limitations"] = tuple(values["scope_limitations"])
        return GetConnectionResultDTO(**values)
