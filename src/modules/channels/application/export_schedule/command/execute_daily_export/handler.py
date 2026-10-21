from uuid import uuid5
from src.modules.channels.application.batch_export.access import BatchExportAccess
from src.modules.channels.application.batch_export.service.start import (
    BatchExportStarter,
)
from src.modules.channels.application.export_schedule.command.execute_daily_export.command import (
    ExecuteDailyExportCommand,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.error import ChannelsError


class ExecuteDailyExportHandler:
    """Планирует следующий день атомарно с запуском актуального пакета."""

    def __init__(self, access: BatchExportAccess) -> None:
        """Принимает порты транзакции фонового календарного события."""
        self.access = access

    async def execute(self, command: ExecuteDailyExportCommand) -> None:
        """Не накапливает старые дни; повтор и устаревшая revision не порождают отправки."""
        a = self.access
        channel = await a.channels.get(EntityIdVO(command.channel_id))
        schedule = await a.schedules.get(command.channel_id)
        now = a.clock.now()
        if (
            not schedule.enabled
            or schedule.revision != command.revision
            or schedule.next_at != command.scheduled_at
            or command.scheduled_at > now
        ):
            return
        schedule.consumed(now)
        await a.schedules.save(schedule)
        if schedule.next_at is not None:
            await a.jobs.daily_export(
                command.tenant_id,
                command.channel_id,
                schedule.revision,
                schedule.next_at,
            )
        # Выключенный/недоступный канал пропускает день, не создавая накопленную очередь.
        if not (await a.feed_links.availability(command.tenant_id)).delivery_configured:
            return
        try:
            a.require_capability(channel)
            channel.ensure_outbound(channel.require_connection().generation)
        except ChannelsError:
            return
        await BatchExportStarter(a).start(
            command.tenant_id,
            channel,
            uuid5(
                command.channel_id,
                "daily:"
                + str(command.revision)
                + ":"
                + command.scheduled_at.isoformat(),
            ),
            None,
            "daily",
            now,
        )
