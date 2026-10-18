from typing import Annotated
from fastapi import Depends
from src.config import dnk_config
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol
from src.modules.channels.presentation.depends.plugin_registry import (
    get_plugin_registry,
)
from src.modules.channels.infrastructure.assembly import ChannelsHandlers
from src.modules.channels.presentation.depends.assembly import (
    assemble_channels_handlers,
)
from src.modules.shared.presentation.persistence.depends import UoWDep

PluginRegistryDep = Annotated[PluginRegistryProtocol, Depends(get_plugin_registry)]


def get_channels_handlers(uow: UoWDep, registry: PluginRegistryDep) -> ChannelsHandlers:
    """Собирает сценарии на одной tenant UoW-зависимости до отправки ответа."""
    return assemble_channels_handlers(
        uow.session,
        registry,
        dnk_config.CHANNELS.credentials_encryption_key.get_secret_value(),
    )


ChannelsHandlersDep = Annotated[ChannelsHandlers, Depends(get_channels_handlers)]
