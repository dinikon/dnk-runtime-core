"""Ручной запуск на транзакции внешней сборки."""

from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.channels.application.sync_run.command.start_sync_run.command import (
    StartSyncRunCommand,
)
from src.modules.channels.application.sync_run.command.start_sync_run.dto import (
    StartSyncRunResultDTO,
)
from src.modules.channels.application.sync_run.service import SyncRuns
from src.modules.channels.domain.channel.error import (
    ChannelNotFoundError,
    InvalidChannelStateError,
)
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.sync_run.error import SyncNotAvailableError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class StartSyncRunHandler:
    """Блокирует Channel до проверки единственного активного запуска."""

    def __init__(
        self,
        channels: ChannelRepositoryProtocol,
        runs: SyncRuns,
        platforms: PlatformRegistry,
    ) -> None:
        """Получает общие порты без SQLAlchemy."""
        self.channels, self.runs, self.platforms = channels, runs, platforms

    async def execute(self, command: StartSyncRunCommand) -> StartSyncRunResultDTO:
        """Не выполняет HTTP-запросов к платформе."""
        channel = await self.channels.get(
            EntityIdVO.from_value(command.channel_id), for_update=True
        )
        if channel is None:
            raise ChannelNotFoundError("Канал не найден.")
        if (
            "publications"
            not in self.platforms.get(
                channel.platform_kind
            ).manifest.supported_capabilities
        ):
            raise SyncNotAvailableError("Платформа не поддерживает публикации.")
        try:
            run = await self.runs.start(
                channel=channel, tenant_id=command.tenant_id, automatic=False
            )
        except InvalidChannelStateError:
            raise SyncNotAvailableError("Сначала проверьте подключение.") from None
        assert run is not None
        return StartSyncRunResultDTO(run.id.uuid, run.status.value)
