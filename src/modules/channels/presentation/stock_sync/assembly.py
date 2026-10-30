from src.modules.channels.infrastructure.registry import InstalledPlatforms
from dataclasses import dataclass
from collections.abc import Callable
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.catalog_item.bindings_facade import (
    CatalogBindingsFacade,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.query_repository import (
    SqlAlchemyCatalogItemQueryRepository,
)
from src.modules.catalog.infrastructure.mutation_lock import PostgresCatalogMutationLock
from src.modules.channels.application.stock_sync.service import (
    StockPlanning,
    StockOperations,
)
from src.modules.channels.infrastructure.catalog_binding.catalog import (
    CatalogBindingGateway,
)
from src.modules.channels.infrastructure.catalog_binding.query_repository import (
    SqlAlchemyCatalogBindingQueryRepository,
)
from src.modules.channels.infrastructure.channel.persistence.repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.channels.infrastructure.stock_sync.repository import (
    SqlAlchemyStockSyncRepository,
)
from src.modules.channels.infrastructure.stock_sync.read import SqlAlchemyStockRead
from src.modules.channels.infrastructure.stock_sync.publication_writer import (
    PublicationStockWriter,
)
from src.modules.channels.infrastructure.stock_sync.jobs import SharedStockJobs
from src.modules.channels.infrastructure.external_publication.persistence.repository import (
    SqlAlchemyExternalPublicationRepository,
)
from src.modules.channels.application.stock_sync.command.prepare_stock_sync.handler import (
    PrepareStockSyncHandler,
)
from src.modules.channels.application.stock_sync.command.apply_stock_sync.handler import (
    ApplyStockSyncHandler,
)
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.shared.presentation.jobs.management import (
    build_scheduled_job_repository,
)


@dataclass(slots=True)
class StockRuntime:
    """Порты и сервисы одного короткого tenant UoW."""

    operations: StockOperations
    planning: StockPlanning
    read: SqlAlchemyStockRead
    prepare: PrepareStockSyncHandler
    apply: ApplyStockSyncHandler


def build_stock_runtime(
    session: AsyncSession, tenant_id: UUID, uuid: Callable[[], UUID] = uuid4
) -> StockRuntime:
    """Собирает Catalog через публичный фасад, Shared Jobs и Domain repositories."""
    shared_jobs = build_scheduled_job_repository(session)
    channels = SqlAlchemyChannelRepository(session, tenant_id)
    states = SqlAlchemyStockSyncRepository(session)
    read = SqlAlchemyStockRead(session, shared_jobs, tenant_id, InstalledPlatforms())
    catalog = CatalogBindingGateway(
        CatalogBindingsFacade(
            SqlAlchemyCatalogItemQueryRepository(session),
            PostgresCatalogMutationLock(session),
        )
    )
    planning = StockPlanning(
        SqlAlchemyCatalogBindingQueryRepository(session),
        catalog,
        read,
        InstalledPlatforms(),
    )
    jobs = SharedStockJobs(shared_jobs)
    clock = UtcClock()
    operations = StockOperations(
        channels=channels, states=states, planning=planning, jobs=jobs, uuid=uuid
    )
    return StockRuntime(
        operations,
        planning,
        read,
        PrepareStockSyncHandler(
            channels=channels,
            states=states,
            planning=planning,
            read=read,
            jobs=jobs,
            clock=clock,
            operations=operations,
        ),
        ApplyStockSyncHandler(
            channels=channels,
            states=states,
            jobs=jobs,
            publications=PublicationStockWriter(
                SqlAlchemyExternalPublicationRepository(session)
            ),
            operations=operations,
            planning=planning,
            clock=clock,
        ),
    )
