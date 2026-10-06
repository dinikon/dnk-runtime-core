from typing import Annotated
from fastapi import Depends
from src.config import dnk_config
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.channels.infrastructure.definitions.registry import CodeChannelRegistry
from src.modules.channels.infrastructure.validation.connection import (
    JsonSchemaConnectionValidator,
)
from src.modules.channels.infrastructure.crypto.cipher import ChannelSecretCipher
from src.modules.channels.infrastructure.persistence.repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.channels.infrastructure.persistence.query_repository import (
    SqlAlchemyChannelQueryRepository,
)
from src.modules.channels.application.command.create_channel.handler import (
    CreateChannelHandler,
)
from src.modules.channels.application.command.update_channel.handler import (
    UpdateChannelHandler,
)
from src.modules.channels.application.command.delete_channel.handler import (
    DeleteChannelHandler,
)
from src.modules.channels.application.query.get_channel.handler import GetChannelHandler
from src.modules.channels.application.query.list_channels.handler import (
    ListChannelsHandler,
)
from src.modules.channels.application.query.list_kinds.handler import ListKindsHandler
from src.modules.channels.application.query.get_kind_config.handler import (
    GetKindConfigHandler,
)


def get_registry():
    return CodeChannelRegistry()


RegistryDep = Annotated[CodeChannelRegistry, Depends(get_registry)]


def get_cipher():
    return ChannelSecretCipher(dnk_config.CHANNELS.secret_encryption_key)


CipherDep = Annotated[ChannelSecretCipher, Depends(get_cipher)]


def get_create_channel_handler(
    uow: UoWDep,
    registry: RegistryDep,
    cipher: CipherDep,
    clock: ClockDep,
    uuids: UuidDep,
):
    return CreateChannelHandler(
        SqlAlchemyChannelRepository(uow.session),
        registry,
        JsonSchemaConnectionValidator(),
        cipher,
        clock,
        uuids,
    )


CreateChannelHandlerDep = Annotated[
    CreateChannelHandler, Depends(get_create_channel_handler)
]


def get_update_channel_handler(
    uow: UoWDep, registry: RegistryDep, cipher: CipherDep, clock: ClockDep
):
    return UpdateChannelHandler(
        SqlAlchemyChannelRepository(uow.session),
        registry,
        JsonSchemaConnectionValidator(),
        cipher,
        clock,
    )


UpdateChannelHandlerDep = Annotated[
    UpdateChannelHandler, Depends(get_update_channel_handler)
]


def get_delete_channel_handler(uow: UoWDep):
    return DeleteChannelHandler(SqlAlchemyChannelRepository(uow.session))


DeleteChannelHandlerDep = Annotated[
    DeleteChannelHandler, Depends(get_delete_channel_handler)
]


def get_get_channel_handler(uow: UoWDep, registry: RegistryDep):
    return GetChannelHandler(SqlAlchemyChannelQueryRepository(uow.session, registry))


GetChannelHandlerDep = Annotated[GetChannelHandler, Depends(get_get_channel_handler)]


def get_list_channels_handler(uow: UoWDep, registry: RegistryDep):
    return ListChannelsHandler(SqlAlchemyChannelQueryRepository(uow.session, registry))


ListChannelsHandlerDep = Annotated[
    ListChannelsHandler, Depends(get_list_channels_handler)
]


def get_list_kinds_handler(registry: RegistryDep):
    return ListKindsHandler(registry)


ListKindsHandlerDep = Annotated[ListKindsHandler, Depends(get_list_kinds_handler)]


def get_get_kind_config_handler(registry: RegistryDep):
    return GetKindConfigHandler(registry)


GetKindConfigHandlerDep = Annotated[
    GetKindConfigHandler, Depends(get_get_kind_config_handler)
]
