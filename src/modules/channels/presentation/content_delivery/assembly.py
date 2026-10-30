from src.modules.channels.application.content_delivery.command.apply_content_reconciliation.handler import (
    ApplyContentReconciliationHandler,
)
from dataclasses import dataclass
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.channels.application.content_delivery.service import ContentDeliveries
from src.modules.channels.application.content_delivery.command.request_content_delivery.handler import (
    RequestContentDeliveryHandler,
)
from src.modules.channels.application.content_delivery.command.request_content_reconciliation.handler import (
    RequestContentReconciliationHandler,
)
from src.modules.channels.application.content_delivery.command.prepare_content_delivery.handler import (
    PrepareContentDeliveryHandler,
)
from src.modules.channels.application.content_delivery.command.apply_content_delivery.handler import (
    ApplyContentDeliveryHandler,
)
from src.modules.channels.application.content_delivery.command.authorize_content_delivery.handler import (
    AuthorizeContentDeliveryHandler,
)
from src.modules.channels.application.content_delivery.query.get_content_deliveries.handler import (
    GetContentDeliveriesHandler,
)
from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.channels.infrastructure.content_delivery.authorization import (
    ContentDeliveryAuthorization,
)
from src.modules.channels.infrastructure.content_delivery.repository import (
    SqlAlchemyContentDeliveryRepository,
)
from src.modules.channels.infrastructure.content_delivery.query_repository import (
    SqlAlchemyContentDeliveryQueryRepository,
)
from src.modules.channels.infrastructure.content_delivery.jobs import (
    SharedContentDeliveryJobs,
)
from src.modules.channels.infrastructure.channel.persistence.repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.channels.presentation.content_media.assembly import (
    build_content_media_runtime,
)
from src.modules.files.application.port.storage import StorageResolverProtocol
from src.modules.identity.application.access.authorization_service_protocol import (
    AuthorizationServiceProtocol,
)
from src.modules.shared.application.crypto.cipher import Cipher
from src.modules.shared.application.persistence.unit_of_work import UnitOfWorkProtocol
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.presentation.jobs.management import (
    build_scheduled_job_repository,
)


@dataclass(slots=True)
class ContentDeliveryRuntime:
    """Обработчики одной tenant-сессии для HTTP и каждого шага Worker."""

    request: RequestContentDeliveryHandler
    reconcile: RequestContentReconciliationHandler
    prepare: PrepareContentDeliveryHandler
    authorize: AuthorizeContentDeliveryHandler
    apply: ApplyContentDeliveryHandler
    apply_reconciliation: ApplyContentReconciliationHandler
    read: GetContentDeliveriesHandler


def build_content_delivery_runtime(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    base_url: str,
    uow: UnitOfWorkProtocol,
    cipher: Cipher,
    clock: ClockPort,
    uuid: UUIdGeneratorProtocol,
    platforms: PlatformRegistry,
    storage: StorageResolverProtocol,
    authorization: AuthorizationServiceProtocol,
) -> ContentDeliveryRuntime:
    """Подключает все репозитории процесса к одному внешнему UoW."""
    media = build_content_media_runtime(
        session=session,
        tenant_id=tenant_id,
        base_url=base_url,
        uow=uow,
        cipher=cipher,
        clock=clock,
        uuid=uuid,
        platforms=platforms,
        storage=storage,
    )
    service = ContentDeliveries(
        galleries=media.galleries,
        transfers=media.transfers,
        channels=SqlAlchemyChannelRepository(session, tenant_id),
        deliveries=SqlAlchemyContentDeliveryRepository(session),
        queries=SqlAlchemyContentDeliveryQueryRepository(session),
        jobs=SharedContentDeliveryJobs(build_scheduled_job_repository(session)),
        authorization=ContentDeliveryAuthorization(
            tenant_id=tenant_id, authorization=authorization
        ),
        platforms=platforms,
        cipher=cipher,
        clock=clock,
        uuid=uuid,
    )
    return ContentDeliveryRuntime(
        RequestContentDeliveryHandler(service),
        RequestContentReconciliationHandler(service),
        PrepareContentDeliveryHandler(service),
        AuthorizeContentDeliveryHandler(service),
        ApplyContentDeliveryHandler(service),
        ApplyContentReconciliationHandler(service),
        GetContentDeliveriesHandler(service),
    )
