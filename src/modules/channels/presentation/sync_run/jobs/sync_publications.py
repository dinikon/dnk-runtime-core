"""Внешняя сборка одного страничного шага синхронизации."""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4
import logging

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config import dnk_config
from src.modules.channels.application.error import (
    VerificationFailure,
    ChannelInputError,
)
from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.channels.application.sync_run.change_preparation import (
    PublicationChangePreparation,
)
from src.modules.channels.application.sync_run.command.prepare_sync_step.command import (
    PrepareSyncStepCommand,
)
from src.modules.channels.application.sync_run.command.prepare_sync_step.handler import (
    PrepareSyncStepHandler,
)
from src.modules.channels.application.sync_run.command.apply_sync_page.command import (
    ApplySyncPageCommand,
)
from src.modules.channels.application.sync_run.command.apply_sync_page.handler import (
    ApplySyncPageHandler,
)
from src.modules.channels.application.sync_run.port.jobs import SyncJob
from src.modules.channels.domain.external_publication.error import (
    InvalidExternalPublicationError,
)
from src.modules.channels.infrastructure.channel.persistence.repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.channels.infrastructure.sync_run.persistence.repository import (
    SqlAlchemySyncRunRepository,
)
from src.modules.channels.infrastructure.external_publication.persistence.repository import (
    SqlAlchemyExternalPublicationRepository,
)
from src.modules.channels.infrastructure.sync_run.jobs import (
    SharedPublicationSyncJobs,
    JOB_TYPE,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.shared.application.crypto.cipher import Cipher
from src.modules.shared.application.crypto.error import (
    CipherNotConfigured,
    CiphertextUnreadable,
)
from src.modules.shared.application.jobs.scheduled_job_deferred import (
    ScheduledJobDeferred,
)
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.presentation.crypto.depends import get_cipher
from src.modules.shared.presentation.jobs.management import (
    build_scheduled_job_repository,
)
from src.modules.tenancy.application.tenant.tenant_admission import TenantUnavailable
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_gate import TenantGate

logger = logging.getLogger(__name__)


class PublicationSyncPayload(BaseModel):
    """Проверяет envelope задания на границе worker."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    tenant_id: UUID
    channel_id: UUID
    connection_id: UUID
    run_id: UUID
    job_id: UUID
    config_revision: int = Field(gt=0, strict=True)

    def to_job(self) -> SyncJob:
        """Передаёт внутрь Application обычный DTO."""
        return SyncJob(
            self.tenant_id,
            self.channel_id,
            self.connection_id,
            self.run_id,
            self.job_id,
            self.config_revision,
        )


class ChannelsSyncPublicationsJobHandler:
    """Оставляет сеть между короткими tenant-транзакциями."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        *,
        platforms: PlatformRegistry | None = None,
        cipher: Cipher | None = None,
    ) -> None:
        """Получает фабрику worker и подменяемые тестами внешние адаптеры."""
        self.sessions = sessions
        self.platforms = platforms or InstalledPlatforms()
        self.cipher = cipher or get_cipher()

    async def handle(self, scheduled: ScheduledJob) -> None:
        """Применяет страницу только при действующем lease и ревизии конфигурации."""
        try:
            payload = PublicationSyncPayload.model_validate(scheduled.payload)
        except ValidationError:
            raise ValueError("Invalid Channels publication payload") from None
        if (
            scheduled.job_type != JOB_TYPE
            or scheduled.tenant_id != payload.tenant_id
            or scheduled.id != payload.job_id
            or not scheduled.lock_token
        ):
            raise ValueError("Invalid Channels publication envelope")
        job = payload.to_job()
        now = lambda: datetime.now(UTC)
        try:
            async with TenantGate(self.sessions).hold(job.tenant_id) as connection:
                await bind_tenant_schema(
                    connection,
                    job.tenant_id,
                    TenantSchemaNaming(dnk_config.SCHEMA_PREFIX),
                )
                sessions = async_sessionmaker(connection, expire_on_commit=False)
                async with UnitOfWork(sessions) as uow:
                    snapshot = await PrepareSyncStepHandler(
                        SqlAlchemyChannelRepository(uow.session, job.tenant_id),
                        SqlAlchemySyncRunRepository(uow.session),
                        SqlAlchemyExternalPublicationRepository(uow.session),
                        SharedPublicationSyncJobs(
                            build_scheduled_job_repository(uow.session)
                        ),
                        now,
                    ).execute(PrepareSyncStepCommand(job, scheduled.lock_token))
                if snapshot is None:
                    return
                platform = self.platforms.get(snapshot.platform_kind)
                page, error_code = None, None
                try:
                    plaintext = self.cipher.decrypt(snapshot.encrypted_credentials)
                    page = await platform.read_publications(
                        config=snapshot.config,
                        credentials=plaintext,
                        checkpoint=snapshot.checkpoint,
                        parent_external_id=snapshot.parent_external_id,
                    )
                    async with UnitOfWork(sessions) as uow:
                        keys = await PublicationChangePreparation(
                            SqlAlchemyExternalPublicationRepository(uow.session)
                        ).dependency_keys(
                            connection_id=job.connection_id,
                            observations=(*page.items, *page.dependencies),
                        )
                    if keys:
                        dependencies = await platform.read_publication_dependencies(
                            config=snapshot.config, credentials=plaintext, keys=keys
                        )
                        page = replace(
                            page, dependencies=(*page.dependencies, *dependencies)
                        )
                except CipherNotConfigured:
                    raise ScheduledJobDeferred(
                        "Channels encryption key unavailable"
                    ) from None
                except CiphertextUnreadable:
                    error_code = "credentials_unreadable"
                except VerificationFailure as error:
                    if (
                        error.retryable
                        and scheduled.attempts < dnk_config.SCHEDULED_JOBS.max_attempts
                    ):
                        raise
                    error_code = error.code
                except ChannelInputError as error:
                    error_code = error.code
                except (ValidationError, ValueError, InvalidExternalPublicationError):
                    error_code = "provider_response_invalid"
                try:
                    async with UnitOfWork(sessions) as uow:
                        await ApplySyncPageHandler(
                            SqlAlchemyChannelRepository(uow.session, job.tenant_id),
                            SqlAlchemySyncRunRepository(uow.session),
                            SqlAlchemyExternalPublicationRepository(uow.session),
                            SharedPublicationSyncJobs(
                                build_scheduled_job_repository(uow.session)
                            ),
                            now,
                            uuid4,
                        ).execute(
                            ApplySyncPageCommand(
                                job,
                                scheduled.lock_token,
                                snapshot.revision,
                                page,
                                platform.manifest.publication_parent_kind,
                                error_code,
                            )
                        )
                except InvalidExternalPublicationError:
                    async with UnitOfWork(sessions) as uow:
                        await ApplySyncPageHandler(
                            SqlAlchemyChannelRepository(uow.session, job.tenant_id),
                            SqlAlchemySyncRunRepository(uow.session),
                            SqlAlchemyExternalPublicationRepository(uow.session),
                            SharedPublicationSyncJobs(
                                build_scheduled_job_repository(uow.session)
                            ),
                            now,
                            uuid4,
                        ).execute(
                            ApplySyncPageCommand(
                                job,
                                scheduled.lock_token,
                                snapshot.revision,
                                None,
                                platform.manifest.publication_parent_kind,
                                "publication_structure_invalid",
                            )
                        )
                logger.info(
                    "Channels publication step committed",
                    extra={
                        "event": "channels.publications.step_committed",
                        "tenant_id": str(job.tenant_id),
                        "run_id": str(job.run_id),
                        "job_id": str(job.job_id),
                    },
                )
        except TenantUnavailable:
            raise ScheduledJobDeferred("Tenant admission unavailable") from None
