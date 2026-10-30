import logging
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config import dnk_config
from src.modules.channels.application.error import VerificationFailure
from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.channels.application.stock_sync.command.prepare_stock_sync.command import (
    PrepareStockSyncCommand,
)
from src.modules.channels.application.stock_sync.command.apply_stock_sync.command import (
    ApplyStockSyncCommand,
)
from src.modules.channels.application.stock_sync.command.consume_catalog_stock_changed.command import (
    ConsumeCatalogStockChangedCommand,
)
from src.modules.channels.application.stock_sync.command.consume_catalog_stock_changed.handler import (
    ConsumeCatalogStockChangedHandler,
)
from src.modules.channels.domain.stock_sync.error import StockSyncError
from src.modules.channels.domain.external_publication.error import (
    InvalidExternalPublicationError,
)
from src.modules.channels.infrastructure.channel.gate import channel_write_gate
from src.modules.channels.infrastructure.stock_sync.jobs import (
    JOB_TYPE,
    CATALOG_EVENT_JOB_TYPE,
)
from src.modules.channels.infrastructure.catalog_binding.query_repository import (
    SqlAlchemyCatalogBindingQueryRepository,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.channels.presentation.stock_sync.assembly import build_stock_runtime
from src.modules.shared.application.crypto.cipher import Cipher
from src.modules.shared.application.crypto.error import (
    CipherNotConfigured,
    CiphertextUnreadable,
)
from src.modules.shared.application.jobs.scheduled_job_deferred import (
    ScheduledJobDeferred,
)
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.shared.domain.events.integration_event import IntegrationEvent
from src.modules.shared.infrastructure.events.sqlalchemy_inbox_repository import (
    SqlAlchemyInboxRepository,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
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


class StockJobPayload(BaseModel):
    """Строгий минимальный envelope Worker."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    channel_id: UUID
    publication_id: UUID


class ChannelsStockJobHandler:
    """Сериализует операции подключения, сохраняя сетевые вызовы вне SQL-транзакции."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        *,
        platforms: PlatformRegistry | None = None,
        cipher: Cipher | None = None,
    ) -> None:
        """Получает фабрику Worker и заменяемые внешние адаптеры."""
        self.sessions, self.platforms, self.cipher = (
            sessions,
            platforms or InstalledPlatforms(),
            cipher or get_cipher(),
        )

    async def handle(self, scheduled: ScheduledJob) -> None:
        """Барьер разделяется с изменением разрешения, конфигурации и привязок."""
        payload = StockJobPayload.model_validate(scheduled.payload)
        if (
            scheduled.job_type != JOB_TYPE
            or scheduled.tenant_id is None
            or not scheduled.lock_token
        ):
            raise ValueError("Invalid Channels stock envelope")
        job = PrepareStockSyncCommand(
            scheduled.tenant_id,
            payload.channel_id,
            payload.publication_id,
            scheduled.id,
            scheduled.lock_token,
        )
        try:
            async with TenantGate(self.sessions).hold(job.tenant_id) as connection:
                await bind_tenant_schema(
                    connection,
                    job.tenant_id,
                    TenantSchemaNaming(dnk_config.SCHEMA_PREFIX),
                )
                async with channel_write_gate(
                    connection, job.tenant_id, job.channel_id
                ):
                    sessions = async_sessionmaker(connection, expire_on_commit=False)
                    error = None
                    while True:
                        async with UnitOfWork(sessions) as uow:
                            prepared = await build_stock_runtime(
                                uow.session, job.tenant_id
                            ).prepare.execute(job)
                        snapshot = prepared.snapshot
                        if snapshot is None:
                            break
                        result, error, owner_id = None, None, None
                        try:
                            platform = self.platforms.get(snapshot.platform_kind)
                            credentials = self.cipher.decrypt(
                                snapshot.encrypted_credentials
                            )
                            publication = snapshot.plan.publication.lookup
                            parent = next(
                                (
                                    v.lookup
                                    for v in snapshot.family
                                    if v.lookup.id == publication.parent_id
                                ),
                                None,
                            )
                            observed = await platform.get_stock(
                                config=snapshot.config,
                                credentials=credentials,
                                publication=publication,
                                parent=parent,
                            )
                            owner = next(
                                (
                                    v.lookup
                                    for v in snapshot.family
                                    if (v.lookup.resource_type, v.lookup.external_id)
                                    == (
                                        observed.stock.resource_type,
                                        observed.stock.external_id,
                                    )
                                ),
                                None,
                            )
                            if owner is None:
                                raise VerificationFailure("stock_ownership_ambiguous")
                            owner_id = owner.id
                            # Повторная короткая проверка перед записью учитывает Catalog, изменённый во время чтения API.
                            if snapshot.direction == "write":
                                async with UnitOfWork(sessions) as uow:
                                    fresh = await build_stock_runtime(
                                        uow.session, job.tenant_id
                                    ).prepare.execute(job)
                                if fresh.snapshot is None:
                                    return
                                snapshot = fresh.snapshot
                            write = snapshot.direction == "write"
                            if write:
                                if owner_id != snapshot.plan.owner.lookup.id:
                                    raise VerificationFailure(
                                        "stock_ownership_ambiguous"
                                    )
                                result = await platform.set_stock(
                                    config=snapshot.config,
                                    credentials=credentials,
                                    publication=owner,
                                    desired=snapshot.plan.desired,
                                )
                            else:
                                result = observed
                        except CipherNotConfigured:
                            raise ScheduledJobDeferred(
                                "Channels encryption key unavailable"
                            ) from None
                        except CiphertextUnreadable:
                            error = "credentials_unreadable"
                        except VerificationFailure as exc:
                            if (
                                exc.retryable
                                and scheduled.attempts
                                < dnk_config.SCHEDULED_JOBS.max_attempts
                            ):
                                raise
                            error = exc.code
                        except StockSyncError as exc:
                            error = exc.code
                        except (
                            ValidationError,
                            ValueError,
                            InvalidExternalPublicationError,
                        ):
                            error = "provider_response_invalid"
                        async with UnitOfWork(sessions) as uow:
                            await build_stock_runtime(
                                uow.session, job.tenant_id
                            ).apply.execute(
                                ApplyStockSyncCommand(
                                    job, snapshot, result, owner_id, error
                                )
                            )
                logger.info(
                    "Channels stock step committed: publication_id=%s job_id=%s reason_code=%s",
                    job.publication_id,
                    job.operation_id,
                    error,
                    extra={
                        "event": "channels.stock.step_committed",
                        "tenant_id": str(job.tenant_id),
                        "channel_id": str(job.channel_id),
                        "job_id": str(job.operation_id),
                        "publication_id": str(job.publication_id),
                        "reason_code": error,
                    },
                )
        except TenantUnavailable:
            raise ScheduledJobDeferred("Tenant admission unavailable") from None


class ChannelsCatalogStockChangedJobHandler:
    """Доставляет событие Catalog во внутренний Inbox без зависимости от брокера."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Получает только фабрику коротких UoW Worker."""
        self.sessions = sessions

    async def handle(self, scheduled: ScheduledJob) -> None:
        """Секретов и сохранённого количества в событии нет."""
        event = IntegrationEvent.from_payload(scheduled.payload)
        if (
            scheduled.job_type != CATALOG_EVENT_JOB_TYPE
            or scheduled.id != event.event_id
            or scheduled.tenant_id != event.tenant_id
            or not scheduled.lock_token
        ):
            raise ValueError("Invalid Catalog stock envelope")
        try:
            async with TenantGate(self.sessions).hold(event.tenant_id) as connection:
                await bind_tenant_schema(
                    connection,
                    event.tenant_id,
                    TenantSchemaNaming(dnk_config.SCHEMA_PREFIX),
                )
                async with UnitOfWork(
                    async_sessionmaker(connection, expire_on_commit=False)
                ) as uow:
                    jobs = build_scheduled_job_repository(uow.session)
                    if not await jobs.owns_current_lease(
                        job_id=scheduled.id,
                        tenant_id=event.tenant_id,
                        lock_token=scheduled.lock_token,
                    ):
                        return
                    runtime = build_stock_runtime(uow.session, event.tenant_id)
                    await ConsumeCatalogStockChangedHandler(
                        operations=runtime.operations,
                        bindings=SqlAlchemyCatalogBindingQueryRepository(uow.session),
                        inbox=SqlAlchemyInboxRepository(uow.session),
                        clock=UtcClock(),
                    ).execute(ConsumeCatalogStockChangedCommand(event))
        except TenantUnavailable:
            raise ScheduledJobDeferred("Tenant admission unavailable") from None
