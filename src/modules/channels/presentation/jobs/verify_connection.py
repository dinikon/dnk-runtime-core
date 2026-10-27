import asyncio
from datetime import UTC, datetime
import logging
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config import dnk_config
from src.modules.channels.application.command.apply_verification.command import (
    ApplyVerificationCommand,
)
from src.modules.channels.application.command.apply_verification.handler import (
    ApplyVerificationHandler,
)
from src.modules.channels.application.command.prepare_verification.command import (
    PrepareVerificationCommand,
)
from src.modules.channels.application.command.prepare_verification.handler import (
    PrepareVerificationHandler,
)
from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.application.port.jobs import VerificationJob
from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.channels.domain.error import (
    InvalidResourceIdentityError,
    InvalidChannelStateError,
)
from src.modules.channels.infrastructure.jobs import SharedVerificationJobs, JOB_TYPE
from src.modules.channels.infrastructure.persistence.repository import (
    SqlAlchemyChannelRepository,
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


class VerificationPayload(BaseModel):
    """Проверяет legacy JSON envelope Shared Jobs на входе в Channels."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    tenant_id: UUID
    channel_id: UUID
    connection_id: UUID
    job_id: UUID
    config_revision: int = Field(gt=0, strict=True)

    def to_job(self) -> VerificationJob:
        """Передаёт в Application обычный типизированный DTO."""
        return VerificationJob(
            self.tenant_id,
            self.channel_id,
            self.connection_id,
            self.job_id,
            self.config_revision,
        )


class ChannelsVerifyConnectionJobHandler:
    """Оркестрирует два коротких UoW и вызов API между ними."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        *,
        platforms: PlatformRegistry | None = None,
        cipher: Cipher | None = None,
    ) -> None:
        """Принимает фабрику worker и подменяемые для contract-тестов адаптеры."""
        self.sessions = sessions
        self.platforms = platforms or InstalledPlatforms()
        self.cipher = cipher or get_cipher()

    async def handle(self, scheduled: ScheduledJob) -> None:
        """Не допускает SQL-транзакции во время сети и применения устаревшего результата."""
        try:
            payload = VerificationPayload.model_validate(scheduled.payload)
        except ValidationError:
            raise ValueError("Invalid Channels verification payload") from None
        if (
            scheduled.job_type != JOB_TYPE
            or scheduled.tenant_id != payload.tenant_id
            or scheduled.id != payload.job_id
            or not scheduled.lock_token
        ):
            raise ValueError("Invalid Channels verification envelope")
        job = payload.to_job()
        try:
            async with TenantGate(self.sessions).hold(job.tenant_id) as connection:
                await bind_tenant_schema(
                    connection,
                    job.tenant_id,
                    TenantSchemaNaming(dnk_config.SCHEMA_PREFIX),
                )
                sessions = async_sessionmaker(connection, expire_on_commit=False)
                async with UnitOfWork(sessions) as uow:
                    repository = SqlAlchemyChannelRepository(uow.session, job.tenant_id)
                    jobs = SharedVerificationJobs(
                        build_scheduled_job_repository(uow.session)
                    )
                    snapshot = await PrepareVerificationHandler(
                        repository, jobs
                    ).execute(PrepareVerificationCommand(job, scheduled.lock_token))
                if snapshot is None:
                    return
                identity, error_code = None, None
                try:
                    plaintext = self.cipher.decrypt(snapshot.encrypted_credentials)
                    async with asyncio.timeout(30):
                        identity = await self.platforms.get(
                            snapshot.platform_kind
                        ).verify(snapshot.config, plaintext)
                except CipherNotConfigured:
                    raise ScheduledJobDeferred(
                        "Channels encryption key unavailable"
                    ) from None
                except CiphertextUnreadable:
                    error_code = "credentials_unreadable"
                except ChannelInputError as error:
                    error_code = error.code
                except InvalidResourceIdentityError:
                    error_code = "resource_identity_unavailable"
                except InvalidChannelStateError:
                    error_code = "stored_channel_invalid"
                except (ValidationError, ValueError):
                    error_code = "provider_response_invalid"
                except TimeoutError:
                    if scheduled.attempts < dnk_config.SCHEDULED_JOBS.max_attempts:
                        raise VerificationFailure(
                            "network_timeout", retryable=True
                        ) from None
                    error_code = "network_timeout"
                except VerificationFailure as error:
                    if (
                        error.retryable
                        and scheduled.attempts < dnk_config.SCHEDULED_JOBS.max_attempts
                    ):
                        raise
                    error_code = error.code
                async with UnitOfWork(sessions) as uow:
                    repository = SqlAlchemyChannelRepository(uow.session, job.tenant_id)
                    jobs = SharedVerificationJobs(
                        build_scheduled_job_repository(uow.session)
                    )
                    await ApplyVerificationHandler(
                        repository, jobs, lambda: datetime.now(UTC)
                    ).execute(
                        ApplyVerificationCommand(
                            job, scheduled.lock_token, identity, error_code
                        )
                    )
                logger.info(
                    "Channels verification processed",
                    extra={
                        "event": "channels.verification.processed",
                        "tenant_id": str(job.tenant_id),
                        "channel_id": str(job.channel_id),
                        "job_id": str(job.job_id),
                    },
                )
        except TenantUnavailable:
            raise ScheduledJobDeferred("Tenant admission unavailable") from None
