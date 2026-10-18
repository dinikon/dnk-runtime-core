from typing import Annotated
from fastapi import Depends
from src.modules.channels.presentation.depends.handlers import ChannelsHandlersDep
from src.modules.channels.application.channel.command.archive_channel.handler import (
    ArchiveChannelHandler,
)
from src.modules.channels.application.channel.command.create_channel.handler import (
    CreateChannelHandler,
)
from src.modules.channels.application.channel.command.create_connection.handler import (
    CreateConnectionHandler,
)
from src.modules.channels.application.channel.command.pause_connection.handler import (
    PauseConnectionHandler,
)
from src.modules.channels.application.channel.command.resume_connection.handler import (
    ResumeConnectionHandler,
)
from src.modules.channels.application.channel.command.update_channel_policy.handler import (
    UpdateChannelPolicyHandler,
)
from src.modules.channels.application.channel.command.update_connection_settings.handler import (
    UpdateConnectionSettingsHandler,
)
from src.modules.channels.application.channel.command.verify_connection.handler import (
    VerifyConnectionHandler,
)
from src.modules.channels.application.channel.query.get_channel.handler import (
    GetChannelHandler,
)
from src.modules.channels.application.channel.query.get_connection.handler import (
    GetConnectionHandler,
)
from src.modules.channels.application.channel.query.get_platform_config.handler import (
    GetPlatformConfigHandler,
)
from src.modules.channels.application.channel.query.list_channels.handler import (
    ListChannelsHandler,
)
from src.modules.channels.application.channel.query.list_platforms.handler import (
    ListPlatformsHandler,
)


def get_archive_channel_handler(handlers: ChannelsHandlersDep) -> ArchiveChannelHandler:
    """Возвращает явно собранный обработчик archive_channel."""
    return handlers.archive_channel


ArchiveChannelHandlerDep = Annotated[
    ArchiveChannelHandler, Depends(get_archive_channel_handler)
]


def get_create_channel_handler(handlers: ChannelsHandlersDep) -> CreateChannelHandler:
    """Возвращает явно собранный обработчик create_channel."""
    return handlers.create_channel


CreateChannelHandlerDep = Annotated[
    CreateChannelHandler, Depends(get_create_channel_handler)
]


def get_create_connection_handler(
    handlers: ChannelsHandlersDep,
) -> CreateConnectionHandler:
    """Возвращает явно собранный обработчик create_connection."""
    return handlers.create_connection


CreateConnectionHandlerDep = Annotated[
    CreateConnectionHandler, Depends(get_create_connection_handler)
]


def get_pause_connection_handler(
    handlers: ChannelsHandlersDep,
) -> PauseConnectionHandler:
    """Возвращает явно собранный обработчик pause_connection."""
    return handlers.pause_connection


PauseConnectionHandlerDep = Annotated[
    PauseConnectionHandler, Depends(get_pause_connection_handler)
]


def get_resume_connection_handler(
    handlers: ChannelsHandlersDep,
) -> ResumeConnectionHandler:
    """Возвращает явно собранный обработчик resume_connection."""
    return handlers.resume_connection


ResumeConnectionHandlerDep = Annotated[
    ResumeConnectionHandler, Depends(get_resume_connection_handler)
]


def get_update_channel_policy_handler(
    handlers: ChannelsHandlersDep,
) -> UpdateChannelPolicyHandler:
    """Возвращает явно собранный обработчик update_channel_policy."""
    return handlers.update_channel_policy


UpdateChannelPolicyHandlerDep = Annotated[
    UpdateChannelPolicyHandler, Depends(get_update_channel_policy_handler)
]


def get_update_connection_settings_handler(
    handlers: ChannelsHandlersDep,
) -> UpdateConnectionSettingsHandler:
    """Возвращает явно собранный обработчик update_connection_settings."""
    return handlers.update_connection_settings


UpdateConnectionSettingsHandlerDep = Annotated[
    UpdateConnectionSettingsHandler, Depends(get_update_connection_settings_handler)
]


def get_verify_connection_handler(
    handlers: ChannelsHandlersDep,
) -> VerifyConnectionHandler:
    """Возвращает явно собранный обработчик verify_connection."""
    return handlers.verify_connection


VerifyConnectionHandlerDep = Annotated[
    VerifyConnectionHandler, Depends(get_verify_connection_handler)
]


def get_get_channel_handler(handlers: ChannelsHandlersDep) -> GetChannelHandler:
    """Возвращает явно собранный обработчик get_channel."""
    return handlers.get_channel


GetChannelHandlerDep = Annotated[GetChannelHandler, Depends(get_get_channel_handler)]


def get_get_connection_handler(handlers: ChannelsHandlersDep) -> GetConnectionHandler:
    """Возвращает явно собранный обработчик get_connection."""
    return handlers.get_connection


GetConnectionHandlerDep = Annotated[
    GetConnectionHandler, Depends(get_get_connection_handler)
]


def get_get_platform_config_handler(
    handlers: ChannelsHandlersDep,
) -> GetPlatformConfigHandler:
    """Возвращает явно собранный обработчик get_platform_config."""
    return handlers.get_platform_config


GetPlatformConfigHandlerDep = Annotated[
    GetPlatformConfigHandler, Depends(get_get_platform_config_handler)
]


def get_list_channels_handler(handlers: ChannelsHandlersDep) -> ListChannelsHandler:
    """Возвращает явно собранный обработчик list_channels."""
    return handlers.list_channels


ListChannelsHandlerDep = Annotated[
    ListChannelsHandler, Depends(get_list_channels_handler)
]


def get_list_platforms_handler(handlers: ChannelsHandlersDep) -> ListPlatformsHandler:
    """Возвращает явно собранный обработчик list_platforms."""
    return handlers.list_platforms


ListPlatformsHandlerDep = Annotated[
    ListPlatformsHandler, Depends(get_list_platforms_handler)
]
