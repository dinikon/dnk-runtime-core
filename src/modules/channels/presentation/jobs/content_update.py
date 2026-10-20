from collections.abc import Callable
from dataclasses import replace
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.config import dnk_config
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol
from src.modules.channels.application.port.plugin_services import (
    PluginContentHttpTransport,
    PluginCallError,
)
from src.modules.channels.application.content_update.command.prepare_content_update_step.command import (
    PrepareContentUpdateStepCommand,
)
from src.modules.channels.application.content_update.command.apply_content_update_step.command import (
    ApplyContentUpdateStepCommand,
)
from src.modules.channels.application.content_update.plugin_contract import (
    SendContentUpdateInputDTO,
)
from src.modules.channels.application.content_update.texts import content_texts
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.infrastructure.jobs import CONTENT_UPDATE_JOB
from src.modules.channels.infrastructure.http.transport import ScopedHttpTransport
from src.modules.channels.infrastructure.security.credentials import (
    ConnectionSecrets,
    ScopedCredentialsAccess,
)
from src.modules.channels.presentation.content_update.assembly import (
    build_content_update_handlers,
)
from src.modules.channels.presentation.depends.plugin_registry import (
    get_plugin_registry,
)
from src.modules.channels.presentation.jobs.scope import tenant_scope
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.shared.application.jobs.scheduled_job_deferred import (
    ScheduledJobDeferred,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.presentation.jobs.management import (
    build_scheduled_job_repository,
)
from src.modules.tenancy.application.tenant.tenant_admission import TenantUnavailable


class ChannelsContentUpdateJobHandler:
    """Выполняет один шаг чтения, отправки или сверки между короткими UoW."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        *,
        registry: PluginRegistryProtocol | None = None,
        transport_factory: Callable[[str], PluginContentHttpTransport] | None = None,
        encryption_key: str | None = None,
    ) -> None:
        """Допускает детерминированные adapters для интеграционных проверок."""
        self.sessions, self.registry = sessions, registry or get_plugin_registry()
        self.transport_factory = transport_factory or ScopedHttpTransport
        self.key = (
            encryption_key
            if encryption_key is not None
            else dnk_config.CHANNELS.credentials_encryption_key.get_secret_value()
        )

    async def handle(self, job: ScheduledJob) -> None:
        """Проверяет tenant admission и lease; после неоднозначной записи выполняет чтение."""
        if (
            job.tenant_id is None
            or not job.lock_token
            or job.job_type != CONTENT_UPDATE_JOB
        ):
            raise ValueError("invalid_content_update_envelope")
        tenant_id, run_id, sequence = (
            job.tenant_id,
            UUID(job.payload["run_id"]),
            int(job.payload["sequence"]),
        )
        try:
            async with tenant_scope(self.sessions, tenant_id) as connection:
                factory = async_sessionmaker(connection, expire_on_commit=False)
                async with UnitOfWork(factory) as uow:
                    if not await build_scheduled_job_repository(
                        uow.session
                    ).owns_current_lease(
                        job_id=job.id,
                        tenant_id=tenant_id,
                        lock_token=job.lock_token,
                    ):
                        return
                    prepared = await build_content_update_handlers(
                        uow.session, self.registry
                    ).prepare.execute(
                        PrepareContentUpdateStepCommand(tenant_id, run_id, sequence)
                    )
                if prepared is None:
                    return
                command = ApplyContentUpdateStepCommand(
                    tenant_id, run_id, sequence, prepared.publication_id, prepared.mode
                )
                credentials = ScopedCredentialsAccess(
                    ConnectionSecrets(self.key),
                    tenant_id,
                    prepared.connection_id,
                    prepared.ciphertext,
                )
                plugin = self.registry.content_updater(
                    prepared.platform_kind,
                    credentials,
                    self.transport_factory(prepared.request.target.settings.endpoint),
                )
                try:
                    if prepared.mode == "send":
                        if prepared.observed_hash is None:
                            raise PluginCallError("content_update_not_ready")
                        outcome = await plugin.send(
                            SendContentUpdateInputDTO(
                                prepared.request, prepared.observed_hash
                            )
                        )
                        if not outcome.accepted:
                            raise PluginCallError("provider_request_rejected")
                    else:
                        outcome = await plugin.inspect(prepared.request)
                        command = replace(
                            command,
                            observed=content_texts(
                                outcome.observed,
                                tuple(text.locale for text in prepared.request.desired),
                            ),
                            issues=outcome.issues,
                        )
                except PluginCallError as error:
                    definitive = error.reason_code in {
                        "permission_denied",
                        "provider_request_rejected",
                        "publication_not_found",
                        "external_content_changed",
                        "content_update_target_unsupported",
                        "invalid_content_payload",
                        "catalog_content_missing",
                        "content_update_not_ready",
                    }
                    command = replace(
                        command,
                        error_code=error.reason_code,
                        uncertain=prepared.mode == "verify"
                        or (prepared.mode == "send" and not definitive),
                    )
                except (ChannelsError, ValueError, TypeError, KeyError):
                    command = replace(
                        command,
                        error_code="invalid_provider_response",
                        uncertain=prepared.mode != "preview",
                    )
                async with UnitOfWork(factory) as uow:
                    if not await build_scheduled_job_repository(
                        uow.session
                    ).owns_current_lease(
                        job_id=job.id,
                        tenant_id=tenant_id,
                        lock_token=job.lock_token,
                        for_update=True,
                    ):
                        raise ScheduledJobDeferred("content_update_lease_changed")
                    await build_content_update_handlers(
                        uow.session, self.registry
                    ).apply.execute(command)
        except TenantUnavailable:
            raise ScheduledJobDeferred("channels_tenant_unavailable") from None
