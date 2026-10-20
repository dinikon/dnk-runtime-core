from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.files.application.port.storage import (
    StorageUnavailableError,
    StorageOwnershipError,
    StorageConfigurationError,
)
from collections.abc import Callable
from dataclasses import replace
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.config import dnk_config
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol
from src.modules.channels.application.port.plugin_services import (
    PluginHttpTransport,
    PluginCallError,
)
from src.modules.channels.application.publication_import.port.images import (
    PublicationImageDownloader,
)
from src.modules.channels.application.publication_import.snapshot import (
    snapshot_for_import,
)
from src.modules.channels.application.publication_import.command.prepare_publication_import_step.command import (
    PreparePublicationImportStepCommand,
)
from src.modules.channels.application.publication_import.command.apply_publication_import_step.command import (
    ApplyPublicationImportStepCommand,
)
from src.modules.channels.application.publication_import.command.cleanup_publication_import.command import (
    CleanupPublicationImportCommand,
)
from src.modules.channels.infrastructure.jobs import IMPORT_JOB, IMPORT_CLEANUP_JOB
from src.modules.channels.infrastructure.http.transport import ScopedHttpTransport
from src.modules.channels.infrastructure.http.image_download import (
    HttpsPublicationImageDownloader,
)
from src.modules.channels.infrastructure.security.credentials import (
    ConnectionSecrets,
    ScopedCredentialsAccess,
)
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.depends.plugin_registry import (
    get_plugin_registry,
)
from src.modules.channels.presentation.publication_import.assembly import (
    build_publication_import_handlers,
)
from src.modules.channels.presentation.jobs.scope import tenant_scope
from src.modules.files.application.port.storage import StorageResolverProtocol
from src.modules.shared.domain.domain_error import DomainError
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


class ChannelsPublicationImportJobHandler:
    """Читает карточку или одну фотографию, не удерживая SQL во время скачивания."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        *,
        registry: PluginRegistryProtocol | None = None,
        transport_factory: Callable[[str], PluginHttpTransport] | None = None,
        downloader: PublicationImageDownloader | None = None,
        storage: StorageResolverProtocol | None = None,
        encryption_key: str | None = None,
    ) -> None:
        """Допускает детерминированные внешние adapters для contract/integration тестов."""
        self.sessions, self.registry = sessions, registry or get_plugin_registry()
        self.transport_factory = transport_factory or ScopedHttpTransport
        self.downloader = downloader or HttpsPublicationImageDownloader()
        self.storage = storage
        self.key = (
            encryption_key
            if encryption_key is not None
            else dnk_config.CHANNELS.credentials_encryption_key.get_secret_value()
        )

    async def handle(self, job: ScheduledJob) -> None:
        """Проверяет lease до чтения и перед commit применения каждого шага."""
        if (
            job.tenant_id is None
            or not job.lock_token
            or job.job_type not in (IMPORT_JOB, IMPORT_CLEANUP_JOB)
        ):
            raise ValueError("invalid_publication_import_envelope")
        tenant_id, identifier = job.tenant_id, UUID(job.payload["preparation_id"])
        try:
            async with tenant_scope(self.sessions, tenant_id) as connection:
                factory = async_sessionmaker(connection, expire_on_commit=False)
                if job.job_type == IMPORT_CLEANUP_JOB:
                    async with UnitOfWork(factory) as uow:
                        if not await build_scheduled_job_repository(
                            uow.session
                        ).owns_current_lease(
                            job_id=job.id,
                            tenant_id=tenant_id,
                            lock_token=job.lock_token,
                            for_update=True,
                        ):
                            return
                        await build_publication_import_handlers(
                            uow.session, self.registry, self.storage
                        ).cleanup.execute(
                            CleanupPublicationImportCommand(tenant_id, identifier)
                        )
                    return
                sequence = int(job.payload["sequence"])
                async with UnitOfWork(factory) as uow:
                    if not await build_scheduled_job_repository(
                        uow.session
                    ).owns_current_lease(
                        job_id=job.id, tenant_id=tenant_id, lock_token=job.lock_token
                    ):
                        return
                    prepared = await build_publication_import_handlers(
                        uow.session, self.registry, self.storage
                    ).prepare.execute(
                        PreparePublicationImportStepCommand(
                            tenant_id, identifier, sequence
                        )
                    )
                if prepared is None:
                    return
                command = ApplyPublicationImportStepCommand(
                    tenant_id, identifier, sequence, image_id=prepared.image_id
                )
                try:
                    if prepared.image_id is not None:
                        image = await self.downloader.download(prepared.image_url)
                        command = replace(
                            command,
                            image_data=image.data,
                            image_content_type=image.content_type,
                        )
                    else:
                        credentials = ScopedCredentialsAccess(
                            ConnectionSecrets(self.key),
                            tenant_id,
                            prepared.connection_id,
                            prepared.ciphertext,
                        )
                        plugin = self.registry.detail_reader(
                            prepared.platform_kind,
                            credentials,
                            self.transport_factory(prepared.request.settings.endpoint),
                        )
                        outcome = await plugin.execute(prepared.request)
                        if (
                            outcome.core.external_id != prepared.request.external_id
                            or outcome.core.resource_type
                            != prepared.request.resource_type
                        ):
                            raise PluginCallError("invalid_publication_identity")
                        command = replace(
                            command,
                            snapshot=snapshot_for_import(
                                outcome, prepared.locales, UtcClock().now()
                            ),
                        )
                except PluginCallError as error:
                    command = replace(command, error_code=error.reason_code)
                except (ChannelsError, ValueError, TypeError, KeyError):
                    command = replace(command, error_code="invalid_provider_response")
                try:
                    async with UnitOfWork(factory) as uow:
                        await build_publication_import_handlers(
                            uow.session, self.registry, self.storage
                        ).apply.execute(command)
                        if not await build_scheduled_job_repository(
                            uow.session
                        ).owns_current_lease(
                            job_id=job.id,
                            tenant_id=tenant_id,
                            lock_token=job.lock_token,
                            for_update=True,
                        ):
                            raise ScheduledJobDeferred(
                                "publication_import_lease_changed"
                            )
                except (
                    DomainError,
                    StorageUnavailableError,
                    StorageOwnershipError,
                    StorageConfigurationError,
                ):
                    if command.image_id is None:
                        raise
                    async with UnitOfWork(factory) as uow:
                        failed = replace(
                            command,
                            image_data=None,
                            image_content_type=None,
                            error_code="image_storage_failed",
                        )
                        await build_publication_import_handlers(
                            uow.session, self.registry, self.storage
                        ).apply.execute(failed)
                        if not await build_scheduled_job_repository(
                            uow.session
                        ).owns_current_lease(
                            job_id=job.id,
                            tenant_id=tenant_id,
                            lock_token=job.lock_token,
                            for_update=True,
                        ):
                            raise ScheduledJobDeferred(
                                "publication_import_lease_changed"
                            )
        except TenantUnavailable:
            raise ScheduledJobDeferred("channels_tenant_unavailable") from None
