from datetime import datetime

from src.modules.reference_data.application.locale.command.sync_locales.command import (
    SyncLocalesCommand,
)
from src.modules.reference_data.application.port.catalog import (
    CatalogRepositoryPort,
    SourcePort,
)
from src.modules.reference_data.application.sync.handler import SyncReferenceDataHandler
from src.modules.reference_data.domain.locale.record import Locale
from src.modules.shared.domain.time.clock_port import ClockPort


class SyncLocalesHandler:
    def __init__(
        self,
        source: SourcePort[Locale],
        repository: CatalogRepositoryPort,
        clock: ClockPort,
    ):
        self._delegate = SyncReferenceDataHandler("locales", source, repository, clock)

    async def execute(self, command: SyncLocalesCommand) -> tuple[str, int, datetime]:
        return await self._delegate.execute()
