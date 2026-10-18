from collections.abc import Callable
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.config import dnk_config
from src.modules.channels.application.sync_run.command.prepare_publication_initialization.command import (
    PreparePublicationInitializationCommand,
)
from src.modules.channels.application.sync_run.command.apply_publication_initialization.command import (
    ApplyPublicationInitializationCommand,
)
from src.modules.channels.application.sync_run.command.complete_publication_initialization.command import (
    CompletePublicationInitializationCommand,
)
from src.modules.channels.application.port.plugin_services import (
    PluginHttpTransport,
    PluginCallError,
)
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol
from src.modules.channels.domain.error import ChannelsUnavailableError
from src.modules.channels.presentation.depends.assembly import (
    assemble_channels_handlers,
)
from src.modules.channels.infrastructure.jobs import PAGE_JOB
from src.modules.channels.infrastructure.http.transport import ScopedHttpTransport
from src.modules.channels.infrastructure.security.credentials import (
    ConnectionSecrets,
    ScopedCredentialsAccess,
)
from src.modules.channels.presentation.depends.plugin_registry import (
    get_plugin_registry,
)
from src.modules.channels.presentation.jobs.scope import tenant_scope
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.shared.application.jobs.scheduled_job_deferred import (
    ScheduledJobDeferred,
)
from src.modules.shared.presentation.jobs.management import (
    build_scheduled_job_repository,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.tenancy.application.tenant.tenant_admission import TenantUnavailable


class ChannelsInitializationJobHandler:
    """Обрабатывает ровно одну порцию с сетью вне SQL-транзакции."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        *,
        registry: PluginRegistryProtocol | None = None,
        transport_factory: Callable[[str], PluginHttpTransport] | None = None,
        encryption_key: str | None = None,
    ) -> None:
        """Принимает внешнюю сборку и допускает contract transport в тестах."""
        self.sessions, self.registry = (sessions, registry or get_plugin_registry())
        self.key = (
            encryption_key
            if encryption_key is not None
            else dnk_config.CHANNELS.credentials_encryption_key.get_secret_value()
        )
        self.transport_factory = transport_factory or self._transport

    @staticmethod
    def _transport(endpoint: str) -> PluginHttpTransport:
        """Создаёт HTTPS transport с едиными ограничениями."""
        return ScopedHttpTransport(
            endpoint,
            max_bytes=dnk_config.CHANNELS.max_response_bytes,
            timeout=dnk_config.CHANNELS.http_timeout_seconds,
        )

    async def handle(self, job: ScheduledJob) -> None:
        """Сохраняет страницу и следующий job только при текущей worker lease."""
        if job.tenant_id is None or not job.lock_token or job.job_type != PAGE_JOB:
            raise ValueError("invalid_channels_initialization_envelope")
        tenant_id = job.tenant_id
        run_id, sequence = (UUID(job.payload["run_id"]), int(job.payload["sequence"]))
        try:
            async with tenant_scope(self.sessions, tenant_id) as connection:
                factory = async_sessionmaker(connection, expire_on_commit=False)
                async with UnitOfWork(factory) as uow:
                    jobs = build_scheduled_job_repository(uow.session)
                    if not await jobs.owns_current_lease(
                        job_id=job.id, tenant_id=tenant_id, lock_token=job.lock_token
                    ):
                        return
                    handlers = assemble_channels_handlers(
                        uow.session, self.registry, self.key
                    )
                    prepared = (
                        await handlers.prepare_publication_initialization.execute(
                            PreparePublicationInitializationCommand(
                                tenant_id, run_id, sequence
                            )
                        )
                    )
                if prepared is None:
                    return
                outcome, error_code, retryable = (None, None, False)
                try:
                    credentials = ScopedCredentialsAccess(
                        ConnectionSecrets(self.key),
                        tenant_id,
                        prepared.connection_id,
                        prepared.ciphertext,
                    )
                    plugin = self.registry.reader(
                        prepared.platform_kind,
                        credentials,
                        self.transport_factory(prepared.request.settings.endpoint),
                    )
                    outcome = await plugin.execute(prepared.request)
                except PluginCallError as error:
                    error_code, retryable = (error.reason_code, error.retryable)
                except ChannelsUnavailableError as error:
                    error_code = str(error)
                async with UnitOfWork(factory) as uow:
                    handlers = assemble_channels_handlers(
                        uow.session, self.registry, self.key
                    )
                    result = await handlers.apply_publication_initialization.execute(
                        ApplyPublicationInitializationCommand(
                            tenant_id,
                            prepared.actor_id,
                            run_id,
                            sequence,
                            outcome,
                            error_code,
                            retryable,
                        )
                    )
                    if result.applied and result.complete:
                        await handlers.complete_publication_initialization.execute(
                            CompletePublicationInitializationCommand(
                                tenant_id, prepared.actor_id, run_id, result.sequence
                            )
                        )
                    if not await build_scheduled_job_repository(
                        uow.session
                    ).owns_current_lease(
                        job_id=job.id,
                        tenant_id=tenant_id,
                        lock_token=job.lock_token,
                        for_update=True,
                    ):
                        raise ScheduledJobDeferred(
                            "channels_initialization_lease_changed"
                        )
        except TenantUnavailable:
            raise ScheduledJobDeferred("channels_tenant_unavailable") from None
