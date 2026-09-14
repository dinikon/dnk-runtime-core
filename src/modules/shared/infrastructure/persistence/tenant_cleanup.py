"""Explicit inventory of shared tenant-owned PostgreSQL records."""

from sqlalchemy import delete

from src.modules.shared.infrastructure.events.integration_inbox_event_model import (
    IntegrationInboxEventModel,
)
from src.modules.shared.infrastructure.events.integration_outbox_event_model import (
    IntegrationOutboxEventModel,
)
from src.modules.shared.infrastructure.jobs.scheduled_job_model import ScheduledJobModel


async def delete_shared_tenant_records(session, tenant_id):
    for model in (
        ScheduledJobModel,
        IntegrationInboxEventModel,
        IntegrationOutboxEventModel,
    ):
        await session.execute(delete(model).where(model.tenant_id == tenant_id))
