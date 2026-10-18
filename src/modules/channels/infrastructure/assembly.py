from src.modules.channels.application.port.jobs import ChannelsJobsProtocol
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol
from src.modules.channels.infrastructure.channel.persistence.repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.channels.infrastructure.channel.persistence.query_repository import (
    SqlAlchemyChannelQueryRepository,
)
from src.modules.channels.infrastructure.sync_run.persistence.repository import (
    SqlAlchemySyncRunRepository,
)
from src.modules.channels.infrastructure.sync_run.persistence.query_repository import (
    SqlAlchemySyncRunQueryRepository,
)
from src.modules.channels.infrastructure.external_publication.persistence.repository import (
    SqlAlchemyExternalPublicationRepository,
)
from src.modules.channels.infrastructure.external_publication.persistence.query_repository import (
    SqlAlchemyExternalPublicationQueryRepository,
)
from src.modules.channels.infrastructure.security.credentials import ConnectionSecrets
from src.modules.channels.infrastructure.channel.adapter.references import (
    ConnectionReferencesAdapter,
)
from src.modules.channels.application.channel.service.connections import (
    ConnectionWorkflow,
)
from src.modules.channels.application.sync_run.service.initialization import (
    InitializationService,
)
from src.modules.reference_data.application.currency.query.validate_currency.handler import (
    ValidateCurrencyHandler,
)
from src.modules.reference_data.infrastructure.currency.persistence.query_repository import (
    SqlAlchemyCurrencyQueryRepository,
)
from src.modules.reference_data.infrastructure.persistence.repository import (
    SqlAlchemyCatalogRepository,
)
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator
from src.modules.channels.application.channel.command.apply_connection_verification.handler import (
    ApplyConnectionVerificationHandler,
)
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
from src.modules.channels.application.channel.command.prepare_connection_verification.handler import (
    PrepareConnectionVerificationHandler,
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
from src.modules.channels.application.sync_run.command.apply_publication_initialization.handler import (
    ApplyPublicationInitializationHandler,
)
from src.modules.channels.application.sync_run.command.complete_publication_initialization.handler import (
    CompletePublicationInitializationHandler,
)
from src.modules.channels.application.sync_run.command.prepare_publication_initialization.handler import (
    PreparePublicationInitializationHandler,
)
from src.modules.channels.application.sync_run.command.start_publication_initialization.handler import (
    StartPublicationInitializationHandler,
)
from src.modules.channels.application.sync_run.query.get_publication_initialization.handler import (
    GetPublicationInitializationHandler,
)
from src.modules.channels.application.external_publication.query.get_external_publication.handler import (
    GetExternalPublicationHandler,
)
from src.modules.channels.application.external_publication.query.list_external_publications.handler import (
    ListExternalPublicationsHandler,
)


@dataclass(frozen=True, slots=True)
class ChannelsHandlers:
    """Содержит явно собранные сценарии одной внешней транзакции."""

    apply_connection_verification: ApplyConnectionVerificationHandler
    archive_channel: ArchiveChannelHandler
    create_channel: CreateChannelHandler
    create_connection: CreateConnectionHandler
    pause_connection: PauseConnectionHandler
    prepare_connection_verification: PrepareConnectionVerificationHandler
    resume_connection: ResumeConnectionHandler
    update_channel_policy: UpdateChannelPolicyHandler
    update_connection_settings: UpdateConnectionSettingsHandler
    verify_connection: VerifyConnectionHandler
    get_channel: GetChannelHandler
    get_connection: GetConnectionHandler
    get_platform_config: GetPlatformConfigHandler
    list_channels: ListChannelsHandler
    list_platforms: ListPlatformsHandler
    apply_publication_initialization: ApplyPublicationInitializationHandler
    complete_publication_initialization: CompletePublicationInitializationHandler
    prepare_publication_initialization: PreparePublicationInitializationHandler
    start_publication_initialization: StartPublicationInitializationHandler
    get_publication_initialization: GetPublicationInitializationHandler
    get_external_publication: GetExternalPublicationHandler
    list_external_publications: ListExternalPublicationsHandler


def build_channels_handlers(
    session: AsyncSession,
    registry: PluginRegistryProtocol,
    encryption_key: str,
    jobs: ChannelsJobsProtocol,
) -> ChannelsHandlers:
    """Подключает все repositories и очередь к одной уже открытой tenant-сессии."""
    clock, identifiers = (UtcClock(), UUID7Generator())
    channels = SqlAlchemyChannelRepository(session)
    runs = SqlAlchemySyncRunRepository(session)
    publications = SqlAlchemyExternalPublicationRepository(session)
    initialization = InitializationService(runs, jobs, clock, identifiers)
    workflow = ConnectionWorkflow(channels, jobs, initialization, clock)
    references = ConnectionReferencesAdapter(
        SqlAlchemyCatalogRepository(session),
        ValidateCurrencyHandler(SqlAlchemyCurrencyQueryRepository(session)),
    )
    secrets = ConnectionSecrets(encryption_key)
    channel_queries = SqlAlchemyChannelQueryRepository(session)
    run_queries = SqlAlchemySyncRunQueryRepository(session, jobs)
    publication_queries = SqlAlchemyExternalPublicationQueryRepository(session)
    return ChannelsHandlers(
        apply_connection_verification=ApplyConnectionVerificationHandler(
            channels, initialization, clock
        ),
        archive_channel=ArchiveChannelHandler(channels, initialization, clock),
        create_channel=CreateChannelHandler(channels, registry, clock, identifiers),
        create_connection=CreateConnectionHandler(
            channels, workflow, registry, references, secrets, clock, identifiers
        ),
        pause_connection=PauseConnectionHandler(channels, initialization, clock),
        prepare_connection_verification=PrepareConnectionVerificationHandler(channels),
        resume_connection=ResumeConnectionHandler(
            channels, workflow, initialization, clock
        ),
        update_channel_policy=UpdateChannelPolicyHandler(channels, clock),
        update_connection_settings=UpdateConnectionSettingsHandler(
            channels, workflow, initialization, registry, references, secrets, clock
        ),
        verify_connection=VerifyConnectionHandler(channels, workflow),
        get_channel=GetChannelHandler(channel_queries),
        get_connection=GetConnectionHandler(channel_queries),
        get_platform_config=GetPlatformConfigHandler(registry),
        list_channels=ListChannelsHandler(channel_queries),
        list_platforms=ListPlatformsHandler(registry),
        apply_publication_initialization=ApplyPublicationInitializationHandler(
            channels, runs, publications, initialization, clock, identifiers
        ),
        complete_publication_initialization=CompletePublicationInitializationHandler(
            runs, clock
        ),
        prepare_publication_initialization=PreparePublicationInitializationHandler(
            channels, runs
        ),
        start_publication_initialization=StartPublicationInitializationHandler(
            channels, initialization
        ),
        get_publication_initialization=GetPublicationInitializationHandler(run_queries),
        get_external_publication=GetExternalPublicationHandler(publication_queries),
        list_external_publications=ListExternalPublicationsHandler(publication_queries),
    )
