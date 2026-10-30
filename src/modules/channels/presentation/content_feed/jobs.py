from uuid import UUID
import logging

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config import dnk_config
from src.modules.channels.application.content_feed.error import FeedBuildError
from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.domain.content_feed.error import ContentFeedError
from src.modules.channels.domain.content_media.error import ContentMediaError
from src.modules.channels.domain.catalog_binding.error import CatalogBindingError
from src.modules.channels.domain.product_representation.error import (
    ProductRepresentationError,
)
from src.modules.channels.infrastructure.channel.gate import channel_write_gate
from src.modules.channels.infrastructure.content_feed.jobs import JOB_TYPE
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.channels.presentation.content_feed.assembly import (
    build_content_feed_runtime,
    ContentFeedRuntime,
)
from src.modules.files.application.port.storage import StorageResolverProtocol
from src.modules.files.infrastructure.assembly import get_storage_resolver
from src.modules.files.application.port.storage import (
    StorageUnavailableError,
    StorageConfigurationError,
    StorageOwnershipError,
)
from src.modules.identity.application.access.authorization_service_protocol import (
    AuthorizationServiceProtocol,
)
from src.modules.identity.presentation.access.depends import (
    default_authorization_service,
)
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
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator
from src.modules.shared.presentation.crypto.depends import get_cipher
from src.modules.tenancy.application.tenant.tenant_admission import TenantUnavailable
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_gate import TenantGate
from src.modules.tenancy.infrastructure.tenant_domain.public_hosts import (
    SqlAlchemyTenantPublicHosts,
)

logger = logging.getLogger(__name__)


class FeedImportJobPayload(BaseModel):
    """Восстанавливает только идентификаторы; секретов в Shared Jobs нет."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    channel_id: UUID
    feed_id: UUID
    operation_id: UUID


class ChannelsFeedImportJobHandler:
    """Выполняет короткий этап без транзакции во время API Prom."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        *,
        platforms: InstalledPlatforms | None = None,
        cipher: Cipher | None = None,
        authorization: AuthorizationServiceProtocol | None = None,
        storage: StorageResolverProtocol | None = None,
    ) -> None:
        """Переиспользует сборку HTTP, Shared Cipher, admission и платформенный registry."""
        self.sessions = sessions
        self.platforms = platforms or InstalledPlatforms()
        self.cipher = cipher or get_cipher()
        self.authorization = authorization or default_authorization_service
        self.storage = storage or get_storage_resolver()

    def _runtime(
        self, uow: UnitOfWork, *, tenant_id: UUID, base_url: str
    ) -> ContentFeedRuntime:
        """Собирает порты одного этапа на общей сессии UoW."""
        return build_content_feed_runtime(
            session=uow.session,
            tenant_id=tenant_id,
            base_url=base_url,
            uow=uow,
            cipher=self.cipher,
            clock=UtcClock(),
            uuid=UUID7Generator(),
            platforms=self.platforms,
            storage=self.storage,
            authorization=self.authorization,
        )

    async def handle(self, scheduled: ScheduledJob) -> None:
        """После сбоя submitting восстанавливается как unknown без повторного POST."""
        if (
            scheduled.job_type != JOB_TYPE
            or scheduled.tenant_id is None
            or not scheduled.lock_token
        ):
            raise ValueError("Invalid feed import envelope")
        try:
            payload = FeedImportJobPayload.model_validate(scheduled.payload)
        except ValidationError:
            raise ValueError("Invalid feed import payload") from None
        tenant_id = scheduled.tenant_id
        identifiers = dict(
            channel_id=payload.channel_id,
            feed_id=payload.feed_id,
            operation_id=payload.operation_id,
            job_id=scheduled.id,
            lock_token=scheduled.lock_token,
        )
        try:
            async with TenantGate(self.sessions).hold(tenant_id) as connection:
                await bind_tenant_schema(
                    connection, tenant_id, TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
                )
                sessions = async_sessionmaker(connection, expire_on_commit=False)
                base_url = "https://localhost"
                try:
                    async with UnitOfWork(sessions) as uow:
                        host = await SqlAlchemyTenantPublicHosts(uow.session).api_host(
                            tenant_id
                        )
                        if host is not None:
                            base_url = "https://" + host
                        step = await self._runtime(
                            uow, tenant_id=tenant_id, base_url=base_url
                        ).imports.claim(**identifiers)
                    if step is None:
                        return
                    importer = self.platforms.feed_importer("prom")
                    credentials = self.cipher.decrypt(step.encrypted_credentials)
                    if step.phase == "queued":
                        async with UnitOfWork(sessions) as uow:
                            prepared = await self._runtime(
                                uow, tenant_id=tenant_id, base_url=base_url
                            ).imports.prepare(step)
                        async with channel_write_gate(
                            connection, tenant_id, payload.channel_id
                        ):
                            async with UnitOfWork(sessions) as uow:
                                started = await self._runtime(
                                    uow, tenant_id=tenant_id, base_url=base_url
                                ).imports.begin(
                                    step, prepared, lock_token=scheduled.lock_token
                                )
                        if not started:
                            return
                        # Prom может скачать XML до ответа на POST. Endpoint нужен
                        # тот же барьер Channel, поэтому отправляем после его освобождения.
                        result = await importer.submit(
                            config=step.config,
                            credentials=credentials,
                            payload=prepared.payload,
                        )
                        async with UnitOfWork(sessions) as uow:
                            await self._runtime(
                                uow, tenant_id=tenant_id, base_url=base_url
                            ).imports.apply_submission(
                                step, result, lock_token=scheduled.lock_token
                            )
                    elif step.phase == "processing":
                        assert step.external_id is not None
                        result = await importer.poll(
                            config=step.config,
                            credentials=credentials,
                            external_id=step.external_id,
                        )
                        async with UnitOfWork(sessions) as uow:
                            await self._runtime(
                                uow, tenant_id=tenant_id, base_url=base_url
                            ).imports.apply_poll(
                                step, result, lock_token=scheduled.lock_token
                            )
                    elif step.phase == "verifying":
                        assert step.encrypted_request is not None
                        results = await importer.verify(
                            config=step.config,
                            credentials=credentials,
                            payload=self.cipher.decrypt(step.encrypted_request),
                        )
                        async with UnitOfWork(sessions) as uow:
                            await self._runtime(
                                uow, tenant_id=tenant_id, base_url=base_url
                            ).imports.apply_verification(
                                step, results, lock_token=scheduled.lock_token
                            )
                    logger.info(
                        "Feed import step committed",
                        extra={
                            "event": "channels.feed_import.step_committed",
                            "tenant_id": str(tenant_id),
                            "feed_id": str(payload.feed_id),
                            "job_id": str(scheduled.id),
                            "phase": step.phase,
                        },
                    )
                except (
                    FeedBuildError,
                    ContentFeedError,
                    ContentMediaError,
                    CatalogBindingError,
                    ProductRepresentationError,
                    VerificationFailure,
                    CipherNotConfigured,
                    CiphertextUnreadable,
                    ValidationError,
                    StorageUnavailableError,
                    StorageConfigurationError,
                    StorageOwnershipError,
                ) as error:
                    if (
                        isinstance(error, ContentFeedError)
                        and error.code == "feed_not_found"
                    ):
                        return
                    code = (
                        error.code
                        if isinstance(
                            error,
                            (
                                FeedBuildError,
                                ContentFeedError,
                                ContentMediaError,
                                CatalogBindingError,
                                ProductRepresentationError,
                                VerificationFailure,
                            ),
                        )
                        else "feed_import_dependencies_unavailable"
                    )
                    async with UnitOfWork(sessions) as uow:
                        await self._runtime(
                            uow, tenant_id=tenant_id, base_url=base_url
                        ).imports.fail(**identifiers, code=code)
        except TenantUnavailable:
            raise ScheduledJobDeferred("Tenant unavailable") from None
