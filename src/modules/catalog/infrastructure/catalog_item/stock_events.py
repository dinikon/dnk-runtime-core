from uuid import UUID, uuid4

from src.modules.catalog.application.catalog_item.stock_events import (
    stock_changed_event,
)
from src.modules.catalog.domain.catalog_item.stock_event import CatalogStockChanged
from src.modules.shared.application.events.outbox_repository_protocol import (
    OutboxRepositoryProtocol,
)
from src.modules.shared.application.jobs.scheduled_job_repository_protocol import (
    ScheduledJobRepositoryProtocol,
)
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob


class CatalogStockEvents:
    """Outbox и внутренняя доставка Shared Jobs принадлежат одной транзакции Catalog."""

    def __init__(
        self, outbox: OutboxRepositoryProtocol, jobs: ScheduledJobRepositoryProtocol
    ) -> None:
        """Не публикует в брокер до commit и не вызывает Channels."""
        self.outbox, self.jobs = outbox, jobs

    async def publish(self, *, tenant_id: UUID, event: CatalogStockChanged) -> None:
        """Сохраняет один envelope для повторяемой внутренней доставки и брокера."""
        integration = stock_changed_event(
            tenant_id=tenant_id, event_id=uuid4(), event=event
        )
        await self.outbox.add(integration)
        await self.jobs.schedule_once(
            ScheduledJob(
                integration.event_id,
                tenant_id,
                integration.event_type,
                integration.to_payload(),
                event.occurred_at,
                "scheduled",
                0,
                None,
                None,
                event.occurred_at,
                event.occurred_at,
            )
        )
