from collections.abc import Callable
from datetime import datetime

from src.modules.channels.application.command.delete_channel.command import (
    DeleteChannelCommand,
)
from src.modules.channels.application.port.jobs import VerificationJobs
from src.modules.channels.domain.error import ChannelNotFoundError
from src.modules.channels.domain.repository import ChannelRepositoryProtocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class DeleteChannelHandler:
    """Удаляет локальный агрегат и отменяет его активные задания."""

    def __init__(
        self,
        repository: ChannelRepositoryProtocol,
        jobs: VerificationJobs,
        clock: Callable[[], datetime],
    ) -> None:
        """Принимает порты общей транзакции."""
        self.repository, self.jobs, self.clock = repository, jobs, clock

    async def execute(self, command: DeleteChannelCommand) -> None:
        """Сначала блокирует Channel, затем задания; внешний API не вызывается."""
        channel = await self.repository.get(
            EntityIdVO.from_value(command.channel_id), for_update=True
        )
        if channel is None:
            raise ChannelNotFoundError("Канал не найден.")
        channel.require_revision(command.expected_revision)
        await self.jobs.cancel(command.tenant_id, channel.id.uuid, self.clock())
        await self.repository.delete(channel.id)
