from src.modules.channels.application.batch_export.access import BatchExportAccess
from src.modules.channels.application.export_schedule.command.update_export_schedule.command import (
    UpdateExportScheduleCommand,
)
from src.modules.channels.application.export_schedule.command.update_export_schedule.dto import (
    UpdateExportScheduleResultDTO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.error import ChannelsUnavailableError


class UpdateExportScheduleHandler:
    """Меняет policy, не затрагивая параметры доступа или generation Connection."""

    def __init__(self, access: BatchExportAccess) -> None:
        """Получает общие порты внешнего tenant UoW."""
        self.access = access

    async def execute(
        self, command: UpdateExportScheduleCommand
    ) -> UpdateExportScheduleResultDTO:
        """Регистрирует новый unique intent; старая версия расписания становится no-op."""
        a = self.access
        channel = await a.channels.get(EntityIdVO(command.channel_id))
        a.require_capability(channel)
        availability = await a.feed_links.availability(command.tenant_id)
        if command.enabled and not availability.delivery_configured:
            raise ChannelsUnavailableError("batch_export_requires_public_host")
        schedule = await a.schedules.get(command.channel_id)
        schedule.change(
            command.enabled,
            command.hour,
            command.minute,
            command.timezone,
            command.expected_revision,
            a.clock.now(),
        )
        await a.schedules.save(schedule)
        if schedule.next_at is not None:
            await a.jobs.daily_export(
                command.tenant_id,
                command.channel_id,
                schedule.revision,
                schedule.next_at,
            )
        return UpdateExportScheduleResultDTO(schedule.revision, schedule.next_at)
