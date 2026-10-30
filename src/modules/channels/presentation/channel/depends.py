from typing import Annotated
from uuid import uuid4

from fastapi import Depends

from src.modules.channels.infrastructure.stock_sync.jobs import SharedStockJobs
from src.modules.channels.presentation.sync_run.depends import SyncRunsDep
from src.modules.channels.infrastructure.settings_catalog import (
    ReferenceChannelSettingsCatalog,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.reference_data.presentation.depends import (
    CatalogRepositoryDep,
    ValidateCurrencyHandlerDep,
)
from src.modules.channels.presentation.depends import (
    tenant_id_from_context,
    utc_now,
    get_platforms,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.presentation.crypto.depends import get_cipher
from src.modules.channels.infrastructure.channel.persistence.repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.channels.infrastructure.channel.persistence.query_repository import (
    SqlAlchemyChannelQueryRepository,
)
from src.modules.channels.infrastructure.channel.jobs import SharedVerificationJobs
from src.modules.shared.presentation.jobs.management import (
    build_scheduled_job_repository,
)
from src.modules.channels.application.channel.service.read_state import ChannelReadState
from src.modules.channels.application.channel.command.create_channel.handler import (
    CreateChannelHandler,
)
from src.modules.channels.application.channel.command.update_channel.handler import (
    UpdateChannelHandler,
)
from src.modules.channels.application.channel.command.verify_connection.handler import (
    VerifyConnectionHandler,
)
from src.modules.channels.application.channel.command.delete_channel.handler import (
    DeleteChannelHandler,
)
from src.modules.channels.application.channel.query.get_channel.handler import (
    GetChannelHandler,
)
from src.modules.channels.application.channel.query.list_channels.handler import (
    ListChannelsHandler,
)
from src.modules.channels.application.query.list_platforms.handler import (
    ListPlatformsHandler,
)


def get_create_channel_handler(
    uow: UoWDep,
    context: AuthenticatedRequestContextDep,
    catalog: CatalogRepositoryDep,
    currencies: ValidateCurrencyHandlerDep,
) -> CreateChannelHandler:
    """Собирает CreateChannel на внешней границе и общей сессии UoW."""
    return CreateChannelHandler(
        SqlAlchemyChannelRepository(uow.session, tenant_id_from_context(context)),
        SharedVerificationJobs(build_scheduled_job_repository(uow.session)),
        get_platforms(),
        get_cipher(),
        utc_now,
        uuid4,
        settings_catalog=ReferenceChannelSettingsCatalog(catalog, currencies),
    )


CreateChannelHandlerDep = Annotated[
    CreateChannelHandler, Depends(get_create_channel_handler)
]


def get_update_channel_handler(
    uow: UoWDep,
    context: AuthenticatedRequestContextDep,
    catalog: CatalogRepositoryDep,
    currencies: ValidateCurrencyHandlerDep,
    sync_runs: SyncRunsDep,
) -> UpdateChannelHandler:
    """Собирает UpdateChannel на внешней границе и общей сессии UoW."""
    return UpdateChannelHandler(
        SqlAlchemyChannelRepository(uow.session, tenant_id_from_context(context)),
        SharedVerificationJobs(build_scheduled_job_repository(uow.session)),
        get_platforms(),
        get_cipher(),
        utc_now,
        uuid4,
        settings_catalog=ReferenceChannelSettingsCatalog(catalog, currencies),
        sync_runs=sync_runs,
    )


UpdateChannelHandlerDep = Annotated[
    UpdateChannelHandler, Depends(get_update_channel_handler)
]


def get_verify_connection_handler(
    uow: UoWDep, context: AuthenticatedRequestContextDep
) -> VerifyConnectionHandler:
    """Собирает VerifyConnection на внешней границе и общей сессии UoW."""
    return VerifyConnectionHandler(
        SqlAlchemyChannelRepository(uow.session, tenant_id_from_context(context)),
        SharedVerificationJobs(build_scheduled_job_repository(uow.session)),
        get_cipher(),
        utc_now,
        uuid4,
    )


VerifyConnectionHandlerDep = Annotated[
    VerifyConnectionHandler, Depends(get_verify_connection_handler)
]


def get_delete_channel_handler(
    uow: UoWDep, context: AuthenticatedRequestContextDep, sync_runs: SyncRunsDep
) -> DeleteChannelHandler:
    """Собирает DeleteChannel на внешней границе и общей сессии UoW."""
    return DeleteChannelHandler(
        SqlAlchemyChannelRepository(uow.session, tenant_id_from_context(context)),
        SharedVerificationJobs(build_scheduled_job_repository(uow.session)),
        utc_now,
        sync_runs=sync_runs,
        stock_jobs=SharedStockJobs(build_scheduled_job_repository(uow.session)),
    )


DeleteChannelHandlerDep = Annotated[
    DeleteChannelHandler, Depends(get_delete_channel_handler)
]


def get_get_channel_handler(
    uow: UoWDep, platforms: Annotated[InstalledPlatforms, Depends(get_platforms)]
) -> GetChannelHandler:
    """Собирает GetChannel на внешней границе и общей сессии UoW."""
    return GetChannelHandler(
        SqlAlchemyChannelQueryRepository(uow.session),
        ChannelReadState(
            SharedVerificationJobs(build_scheduled_job_repository(uow.session)),
            platforms,
        ),
    )


GetChannelHandlerDep = Annotated[GetChannelHandler, Depends(get_get_channel_handler)]


def get_list_channels_handler(
    uow: UoWDep, platforms: Annotated[InstalledPlatforms, Depends(get_platforms)]
) -> ListChannelsHandler:
    """Собирает ListChannels на внешней границе и общей сессии UoW."""
    return ListChannelsHandler(
        SqlAlchemyChannelQueryRepository(uow.session),
        ChannelReadState(
            SharedVerificationJobs(build_scheduled_job_repository(uow.session)),
            platforms,
        ),
    )


ListChannelsHandlerDep = Annotated[
    ListChannelsHandler, Depends(get_list_channels_handler)
]


def get_list_platforms_handler(
    platforms: Annotated[InstalledPlatforms, Depends(get_platforms)],
) -> ListPlatformsHandler:
    """Собирает ListPlatforms на внешней границе и общей сессии UoW."""
    return ListPlatformsHandler(platforms)


ListPlatformsHandlerDep = Annotated[
    ListPlatformsHandler, Depends(get_list_platforms_handler)
]
