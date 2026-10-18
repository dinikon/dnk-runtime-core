from collections.abc import Callable
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.config import dnk_config
from src.modules.channels.application.channel.command.prepare_connection_verification.command import (
    PrepareConnectionVerificationCommand,
)
from src.modules.channels.application.channel.command.apply_connection_verification.command import (
    ApplyConnectionVerificationCommand,
)
from src.modules.channels.application.plugin_contract import (
    VerifyConnectionInputDTO,
    VerifyConnectionOutcomeDTO,
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
from src.modules.channels.infrastructure.jobs import VERIFY_JOB
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


class ChannelsVerificationJobHandler:
    """Разделяет подготовку, внешний GET и атомарное применение verification."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        *,
        registry: PluginRegistryProtocol | None = None,
        transport_factory: Callable[[str], PluginHttpTransport] | None = None,
        encryption_key: str | None = None,
    ) -> None:
        """Принимает process-scoped зависимости без HTTP request/session."""
        self.sessions, self.registry = (sessions, registry or get_plugin_registry())
        self.key = (
            encryption_key
            if encryption_key is not None
            else dnk_config.CHANNELS.credentials_encryption_key.get_secret_value()
        )
        self.transport_factory = transport_factory or self._transport

    @staticmethod
    def _transport(endpoint: str) -> PluginHttpTransport:
        """Собирает ограниченный transport из deployment settings."""
        return ScopedHttpTransport(
            endpoint,
            max_bytes=dnk_config.CHANNELS.max_response_bytes,
            timeout=dnk_config.CHANNELS.http_timeout_seconds,
        )

    async def handle(self, job: ScheduledJob) -> None:
        """Проверяет lease до HTTP и перед общим commit результата и init job."""
        if job.tenant_id is None or not job.lock_token or job.job_type != VERIFY_JOB:
            raise ValueError("invalid_channels_verification_envelope")
        tenant_id = job.tenant_id
        channel_id, actor_id = (
            UUID(job.payload["channel_id"]),
            UUID(job.payload["actor_id"]),
        )
        generation = int(job.payload["generation"])
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
                    prepared = await handlers.prepare_connection_verification.execute(
                        PrepareConnectionVerificationCommand(
                            tenant_id, actor_id, channel_id, generation, job.id
                        )
                    )
                if prepared is None:
                    return
                try:
                    credentials = ScopedCredentialsAccess(
                        ConnectionSecrets(self.key),
                        tenant_id,
                        prepared.connection_id,
                        prepared.ciphertext,
                    )
                    plugin = self.registry.verifier(
                        prepared.platform_kind,
                        credentials,
                        self.transport_factory(prepared.settings.endpoint),
                    )
                    outcome = await plugin.execute(
                        VerifyConnectionInputDTO(prepared.settings)
                    )
                except PluginCallError as error:
                    if (
                        error.retryable
                        and job.attempts < dnk_config.SCHEDULED_JOBS.max_attempts
                    ):
                        raise
                    outcome = VerifyConnectionOutcomeDTO(None, error.reason_code)
                except ChannelsUnavailableError as error:
                    outcome = VerifyConnectionOutcomeDTO(None, str(error))
                async with UnitOfWork(factory) as uow:
                    handlers = assemble_channels_handlers(
                        uow.session, self.registry, self.key
                    )
                    await handlers.apply_connection_verification.execute(
                        ApplyConnectionVerificationCommand(
                            tenant_id, actor_id, channel_id, generation, job.id, outcome
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
                            "channels_verification_lease_changed"
                        )
        except TenantUnavailable:
            raise ScheduledJobDeferred("channels_tenant_unavailable") from None
