from src.modules.channels.application.batch_export.artifacts import export_artifact_id
from src.modules.channels.application.batch_export.command.prepare_export_artifact_page.command import (
    PrepareExportArtifactPageCommand,
)
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
import hashlib
from tempfile import SpooledTemporaryFile
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.config import dnk_config
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol
from src.modules.channels.application.port.plugin_services import (
    PluginBatchHttpTransport,
    PluginCallError,
)
from src.modules.channels.application.batch_export.command.prepare_batch_export_step.command import (
    PrepareBatchExportStepCommand,
)
from src.modules.channels.application.batch_export.command.prepare_batch_export_step.dto import (
    PreparedBatchExportStepDTO,
)
from src.modules.channels.application.batch_export.command.apply_batch_export_step.command import (
    ApplyBatchExportStepCommand,
)
from src.modules.channels.application.export_schedule.command.execute_daily_export.command import (
    ExecuteDailyExportCommand,
)
from src.modules.channels.infrastructure.jobs import BATCH_EXPORT_JOB, DAILY_EXPORT_JOB
from src.modules.channels.infrastructure.http.transport import ScopedHttpTransport
from src.modules.channels.infrastructure.security.credentials import (
    ConnectionSecrets,
    ScopedCredentialsAccess,
)
from src.modules.channels.presentation.batch_export.assembly import (
    build_batch_export_handlers,
    BatchExportHandlers,
)
from src.modules.channels.presentation.depends.plugin_registry import (
    get_plugin_registry,
)
from src.modules.channels.presentation.jobs.scope import tenant_scope
from src.modules.files.application.port.storage import StorageResolverProtocol
from src.modules.files.infrastructure.assembly import (
    build_artifact_files_facade,
    get_storage_resolver,
)
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


class ChannelsBatchExportJobHandler:
    """Выполняет один bounded шаг между короткими SQL UoW; не повторяет POST при recovery."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        *,
        registry: PluginRegistryProtocol | None = None,
        transport_factory: Callable[[str], PluginBatchHttpTransport] | None = None,
        encryption_key: str | None = None,
        storage: StorageResolverProtocol | None = None,
    ) -> None:
        """Позволяет проверить полный процесс с детерминированным provider adapter."""
        self.sessions, self.registry = sessions, registry or get_plugin_registry()
        self.transport_factory = transport_factory or ScopedHttpTransport
        self.key = (
            encryption_key
            if encryption_key is not None
            else dnk_config.CHANNELS.credentials_encryption_key.get_secret_value()
        )
        self.storage = storage or get_storage_resolver()

    def handlers(self, session: AsyncSession) -> BatchExportHandlers:
        """Собирает конкретные use cases текущей внешней транзакции."""
        return build_batch_export_handlers(session, self.registry)

    async def owns(
        self, session: AsyncSession, job: ScheduledJob, *, lock: bool = False
    ) -> bool:
        """Проверяет tenant и актуальную lease перед изменением пакета."""
        return await build_scheduled_job_repository(session).owns_current_lease(
            job_id=job.id,
            tenant_id=job.tenant_id,
            lock_token=job.lock_token,
            for_update=lock,
        )

    async def handle(self, job: ScheduledJob) -> None:
        """Разделяет календарное намерение и сетевой шаг пакетного экспорта."""
        if (
            job.tenant_id is None
            or not job.lock_token
            or job.job_type not in (BATCH_EXPORT_JOB, DAILY_EXPORT_JOB)
        ):
            raise ValueError("invalid_batch_export_envelope")
        try:
            async with tenant_scope(self.sessions, job.tenant_id) as connection:
                factory = async_sessionmaker(connection, expire_on_commit=False)
                async with UnitOfWork(factory) as uow:
                    if not await self.owns(uow.session, job, lock=True):
                        return
                    if job.job_type == DAILY_EXPORT_JOB:
                        await self.handlers(uow.session).daily.execute(
                            ExecuteDailyExportCommand(
                                job.tenant_id,
                                UUID(job.payload["channel_id"]),
                                int(job.payload["revision"]),
                                datetime.fromisoformat(job.payload["scheduled_at"]),
                            )
                        )
                        return
                    prepared = await self.handlers(uow.session).prepare.execute(
                        PrepareBatchExportStepCommand(
                            job.tenant_id,
                            UUID(job.payload["run_id"]),
                            int(job.payload["sequence"]),
                        )
                    )
                if prepared is None:
                    return
                credentials = ScopedCredentialsAccess(
                    ConnectionSecrets(self.key),
                    job.tenant_id,
                    prepared.connection_id,
                    prepared.ciphertext,
                )
                plugin = self.registry.batch_exporter(
                    prepared.platform_kind,
                    credentials,
                    self.transport_factory(prepared.settings.endpoint),
                )
                command = ApplyBatchExportStepCommand(
                    job.tenant_id,
                    prepared.run_id,
                    prepared.sequence,
                    prepared.mode,
                    item=prepared.item,
                )
                try:
                    if prepared.mode == "preparing":
                        command = replace(
                            command,
                            inspection=await plugin.inspect(
                                prepared.settings, prepared.item
                            ),
                        )
                    elif prepared.mode == "checking":
                        command = replace(
                            command,
                            identities=await plugin.identities(
                                prepared.settings, prepared.cursor
                            ),
                        )
                    elif prepared.mode == "building":
                        with SpooledTemporaryFile(
                            max_size=1024 * 1024, mode="w+b"
                        ) as target:
                            plugin.begin(target)
                            after = None
                            while True:
                                async with UnitOfWork(factory) as uow:
                                    result = await self.handlers(
                                        uow.session
                                    ).artifact_page.execute(
                                        PrepareExportArtifactPageCommand(
                                            prepared.run_id, prepared.sequence, after
                                        )
                                    )
                                if result is None:
                                    return
                                page = result.items
                                if not page:
                                    break
                                for item in page:
                                    plugin.append(target, item)
                                after = page[-1].publication_id
                                if target.tell() > 256 * 1024 * 1024:
                                    raise PluginCallError("export_feed_too_large")
                            plugin.end(target)
                            size = target.tell()
                            target.seek(0)
                            digest = hashlib.file_digest(target, "sha256").hexdigest()
                            target.seek(0)
                            async with UnitOfWork(factory) as uow:
                                if not await self.owns(uow.session, job, lock=True):
                                    raise ScheduledJobDeferred(
                                        "batch_export_lease_changed"
                                    )
                                location = await build_artifact_files_facade(
                                    uow.session
                                ).reserve(
                                    job.tenant_id,
                                    export_artifact_id(prepared.run_id),
                                    "catalog-texts.xml",
                                    "application/xml",
                                    size,
                                    self.handlers(uow.session).access.clock.now(),
                                )
                            await self.storage.resolve(location.location).put(
                                location.location,
                                location.key,
                                target,
                                size,
                                "application/xml",
                            )
                            command = replace(
                                command, artifact_hash=digest, artifact_size=size
                            )
                    elif prepared.mode == "submit":
                        url = prepared.feed_url
                        if url is None:
                            raise PluginCallError("batch_export_feed_unconfigured")
                        command = replace(
                            command,
                            remote_id=await plugin.submit(prepared.settings, url),
                        )
                    elif prepared.mode == "processing":
                        command = replace(
                            command, poll=await plugin.poll(prepared.remote_id)
                        )
                    elif prepared.mode == "verifying":
                        command = replace(
                            command,
                            issues=await plugin.verify(
                                prepared.settings, prepared.item
                            ),
                        )
                except PluginCallError as error:
                    definitive = error.reason_code in (
                        "provider_request_rejected",
                        "permission_denied",
                        "invalid_export_payload",
                    )
                    command = replace(
                        command,
                        error_code=error.reason_code,
                        uncertain=prepared.mode == "submit" and not definitive,
                    )
                async with UnitOfWork(factory) as uow:
                    if not await self.owns(uow.session, job, lock=True):
                        raise ScheduledJobDeferred("batch_export_lease_changed")
                    if command.mode == "building" and command.artifact_size is not None:
                        await build_artifact_files_facade(uow.session).confirm(
                            export_artifact_id(command.run_id), command.artifact_size
                        )
                    await self.handlers(uow.session).apply.execute(command)
        except TenantUnavailable:
            raise ScheduledJobDeferred("channels_tenant_unavailable") from None
