from src.modules.channels.application.content_delivery.command.apply_content_reconciliation.command import (
    ApplyContentReconciliationCommand,
)
import logging
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config import dnk_config
from src.modules.channels.application.content_delivery.command.prepare_content_delivery.command import (
    PrepareContentDeliveryCommand,
)
from src.modules.channels.application.content_delivery.command.authorize_content_delivery.command import (
    AuthorizeContentDeliveryCommand,
)
from src.modules.channels.application.content_delivery.command.apply_content_delivery.command import (
    ApplyContentDeliveryCommand,
)
from src.modules.channels.application.content_delivery.contracts import (
    ContentDeliveryResult,
    ContentReconciliationResult,
    ContentWriteOutcome,
    ContentMediaChecksum,
)
from src.modules.channels.application.content_delivery.service import (
    ContentDeliveryDeferred,
)
from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.channels.domain.catalog_binding.error import CatalogBindingError
from src.modules.channels.domain.channel.error import ChannelNotFoundError
from src.modules.channels.domain.content_media.error import ContentMediaError
from src.modules.channels.infrastructure.channel.gate import channel_write_gate
from src.modules.channels.infrastructure.content_delivery.jobs import JOB_TYPE
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.channels.presentation.content_delivery.assembly import (
    ContentDeliveryRuntime,
    build_content_delivery_runtime,
)
from src.modules.files.application.port.storage import (
    StorageResolverProtocol,
    StorageUnavailableError,
)
from src.modules.files.infrastructure.assembly import get_storage_resolver
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


class ContentDeliveryJobPayload(BaseModel):
    """Строгий envelope содержит только идентификаторы владельцев и цели."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    channel_id: UUID
    group_id: UUID
    representation_id: UUID
    publication_id: UUID


class ChannelsContentDeliveryJobHandler:
    """Выполняет один внешний шаг между короткими tenant UoW."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        *,
        platforms: PlatformRegistry | None = None,
        cipher: Cipher | None = None,
        authorization: AuthorizationServiceProtocol | None = None,
        storage: StorageResolverProtocol | None = None,
    ) -> None:
        """Использует общие адаптеры приложения и заменяемые контракты тестов."""
        self._sessions = sessions
        self._platforms = platforms or InstalledPlatforms()
        self._cipher = cipher or get_cipher()
        self._authorization = authorization or default_authorization_service
        self._storage = storage or get_storage_resolver()

    def _runtime(
        self, uow: UnitOfWork, tenant_id: UUID, base_url: str
    ) -> ContentDeliveryRuntime:
        """Собирает только текущий шаг, не передавая session в Application."""
        return build_content_delivery_runtime(
            session=uow.session,
            tenant_id=tenant_id,
            base_url=base_url,
            uow=uow,
            cipher=self._cipher,
            clock=UtcClock(),
            uuid=UUID7Generator(),
            platforms=self._platforms,
            storage=self._storage,
            authorization=self._authorization,
        )

    async def handle(self, scheduled: ScheduledJob) -> None:
        """Сохранённый in_flight после сбоя восстанавливается исключительно через GET."""
        try:
            payload = ContentDeliveryJobPayload.model_validate(scheduled.payload)
        except ValidationError:
            raise ValueError("Invalid Channels content payload") from None
        if (
            scheduled.job_type != JOB_TYPE
            or scheduled.tenant_id is None
            or not scheduled.lock_token
        ):
            raise ValueError("Invalid Channels content envelope")
        tenant_id = scheduled.tenant_id
        try:
            async with TenantGate(self._sessions).hold(tenant_id) as connection:
                await bind_tenant_schema(
                    connection, tenant_id, TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
                )
                sessions = async_sessionmaker(connection, expire_on_commit=False)
                async with UnitOfWork(sessions) as uow:
                    host = await SqlAlchemyTenantPublicHosts(uow.session).api_host(
                        tenant_id
                    )
                if host is None:
                    raise ScheduledJobDeferred("Tenant media host unavailable")
                base_url = "https://" + host
                async with UnitOfWork(sessions) as uow:
                    prepared = await self._runtime(
                        uow, tenant_id, base_url
                    ).prepare.execute(
                        PrepareContentDeliveryCommand(
                            tenant_id=tenant_id,
                            channel_id=payload.channel_id,
                            group_id=payload.group_id,
                            representation_id=payload.representation_id,
                            publication_id=payload.publication_id,
                            job_id=scheduled.id,
                            lock_token=scheduled.lock_token,
                        )
                    )
                snapshot = prepared.snapshot
                if snapshot is None:
                    return
                # Под барьером больше нет Catalog FOR UPDATE: команды редактора могут ожидать Channel, удерживая Catalog.
                async with channel_write_gate(
                    connection, tenant_id, payload.channel_id
                ):
                    async with UnitOfWork(sessions) as uow:
                        runtime = self._runtime(uow, tenant_id, base_url)
                        allowed = await runtime.authorize.execute(
                            AuthorizeContentDeliveryCommand(
                                tenant_id, snapshot, scheduled.lock_token
                            )
                        )
                    result: ContentDeliveryResult | ContentReconciliationResult
                    if not allowed.allowed:
                        if snapshot.reconcile:
                            result = ContentReconciliationResult(
                                False, error_code="content_context_changed"
                            )
                        else:
                            result = ContentDeliveryResult(
                                ContentWriteOutcome.REJECTED,
                                error_code="content_context_changed",
                            )
                    else:
                        try:
                            credentials = self._cipher.decrypt(
                                snapshot.encrypted_credentials
                            )
                            platform = self._platforms.get(snapshot.platform_kind)
                            if snapshot.reconcile:
                                checksums: tuple[ContentMediaChecksum, ...] = ()
                                if snapshot.media_sources:
                                    try:
                                        files = await runtime.files.checksums(
                                            tuple(
                                                v.file for v in snapshot.media_sources
                                            )
                                        )
                                        by_file = {v.file_id: v.sha256 for v in files}
                                        checksums = tuple(
                                            ContentMediaChecksum(
                                                v.media_id, by_file[v.file.file_id]
                                            )
                                            for v in snapshot.media_sources
                                        )
                                    except (ContentMediaError, StorageUnavailableError):
                                        # Недоступный исходник не становится доказательством успеха.
                                        pass
                                result = await platform.reconcile_content(
                                    config=snapshot.config,
                                    credentials=credentials,
                                    request=snapshot.request,
                                    known_media=snapshot.known_media,
                                    media_checksums=checksums,
                                )
                            else:
                                result = await platform.send_content(
                                    config=snapshot.config,
                                    credentials=credentials,
                                    request=snapshot.request,
                                )
                        except CiphertextUnreadable:
                            result = (
                                ContentReconciliationResult(
                                    False, error_code="credentials_unreadable"
                                )
                                if snapshot.reconcile
                                else ContentDeliveryResult(
                                    ContentWriteOutcome.UNKNOWN,
                                    error_code="credentials_unreadable",
                                )
                            )
                    async with UnitOfWork(sessions) as uow:
                        runtime = self._runtime(uow, tenant_id, base_url)
                        if snapshot.reconcile:
                            assert isinstance(result, ContentReconciliationResult)
                            applied = await runtime.apply_reconciliation.execute(
                                ApplyContentReconciliationCommand(
                                    tenant_id, snapshot, scheduled.lock_token, result
                                )
                            )
                        else:
                            assert isinstance(result, ContentDeliveryResult)
                            applied = await runtime.apply.execute(
                                ApplyContentDeliveryCommand(
                                    tenant_id, snapshot, scheduled.lock_token, result
                                )
                            )
                logger.info(
                    "Channels content step committed",
                    extra={
                        "event": "channels.content.step_committed",
                        "tenant_id": str(tenant_id),
                        "job_id": str(scheduled.id),
                        "publication_id": str(payload.publication_id),
                        "reason_code": result.error_code,
                        "applied": applied.applied,
                    },
                )
        except (TenantUnavailable, ContentDeliveryDeferred, CipherNotConfigured):
            raise ScheduledJobDeferred("Channels content step deferred") from None
        except (CatalogBindingError, ChannelNotFoundError):
            # Удалённый владелец не получает новых внешних вызовов.
            return
