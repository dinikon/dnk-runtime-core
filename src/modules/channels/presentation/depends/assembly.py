from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol
from src.modules.channels.infrastructure.assembly import (
    ChannelsHandlers,
    build_channels_handlers,
)
from src.modules.channels.infrastructure.jobs import ScheduledChannelsJobs
from src.modules.shared.presentation.jobs.management import (
    build_schedule_scheduled_job_use_case,
    build_scheduled_job_repository,
)


def assemble_channels_handlers(
    session: AsyncSession, registry: PluginRegistryProtocol, encryption_key: str
) -> ChannelsHandlers:
    """Собирает public shared jobs и Channels на одной внешней сессии/admission."""
    return build_channels_handlers(
        session,
        registry,
        encryption_key,
        ScheduledChannelsJobs(
            build_schedule_scheduled_job_use_case(session=session),
            build_scheduled_job_repository(session),
        ),
    )
