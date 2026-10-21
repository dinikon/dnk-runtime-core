from datetime import datetime
from uuid import UUID
from src.modules.channels.application.batch_export.access import BatchExportAccess
from src.modules.channels.domain.batch_export.aggregate import BatchExportRun
from src.modules.channels.domain.channel.aggregate import Channel
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsUnavailableError,
)


class BatchExportStarter:
    """Общий сервис ручного и календарного запуска без вызова одного use case из другого."""

    def __init__(self, access: BatchExportAccess) -> None:
        """Принимает порты текущей транзакции."""
        self.access = access

    async def start(
        self,
        tenant_id: UUID,
        channel: Channel,
        run_id: UUID,
        actor_id: UUID | None,
        trigger: str,
        now: datetime,
        delivery_mode: str = "provider",
    ) -> BatchExportRun:
        """Сериализует запуск по Channel и возвращает существующее принятое намерение."""
        a = self.access
        a.require_capability(channel)
        connection = channel.require_connection()
        existing = await a.runs.find(run_id)
        if existing is not None:
            if (
                existing.channel_id != channel.id.uuid
                or existing.delivery_mode != delivery_mode
            ):
                raise ChannelsConflictError("batch_export_id_reused")
            return existing
        active = await a.runs.active(connection.id.uuid)
        if active is not None:
            if active.delivery_mode != delivery_mode:
                raise ChannelsConflictError("batch_export_mode_conflict")
            return active
        channel.ensure_outbound(connection.generation)
        availability = await a.feed_links.availability(tenant_id)
        if not availability.feed_available:
            raise ChannelsUnavailableError("batch_export_feed_unconfigured")
        if delivery_mode == "provider" and not availability.delivery_configured:
            raise ChannelsUnavailableError("batch_export_requires_public_host")
        run = BatchExportRun.create(
            run_id,
            channel.id.uuid,
            connection.id.uuid,
            actor_id,
            connection.generation,
            trigger,
            now,
            delivery_mode=delivery_mode,
        )
        await a.runs.add(run)
        await a.jobs.batch_export(tenant_id, run.id, run.sequence, now)
        return run
