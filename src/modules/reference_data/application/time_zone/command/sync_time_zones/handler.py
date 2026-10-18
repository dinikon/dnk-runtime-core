from datetime import datetime

from src.modules.reference_data.application.port.catalog import (
    CatalogRepositoryPort,
    SourcePort,
)
from src.modules.reference_data.application.sync.handler import SyncReferenceDataHandler
from src.modules.reference_data.application.time_zone.command.sync_time_zones.command import (
    SyncTimeZonesCommand,
)
from src.modules.reference_data.domain.time_zone.record import TimeZone
from src.modules.shared.domain.time.clock_port import ClockPort


class SyncTimeZonesHandler:
    def __init__(
        self,
        source: SourcePort[TimeZone],
        repository: CatalogRepositoryPort,
        clock: ClockPort,
    ):
        self._delegate = SyncReferenceDataHandler(
            "time-zones", source, repository, clock
        )

    async def execute(self, command: SyncTimeZonesCommand) -> tuple[str, int, datetime]:
        return await self._delegate.execute()
