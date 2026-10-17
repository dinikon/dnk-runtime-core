from datetime import datetime

from src.modules.reference_data.application.country.command.sync_countries.command import (
    SyncCountriesCommand,
)
from src.modules.reference_data.application.port.catalog import (
    CatalogRepositoryPort,
    SourcePort,
)
from src.modules.reference_data.application.sync.handler import SyncReferenceDataHandler
from src.modules.reference_data.domain.country.record import Country
from src.modules.shared.domain.time.clock_port import ClockPort


class SyncCountriesHandler:
    def __init__(
        self,
        source: SourcePort[Country],
        repository: CatalogRepositoryPort,
        clock: ClockPort,
    ):
        self._delegate = SyncReferenceDataHandler(
            "countries", source, repository, clock
        )

    async def execute(self, command: SyncCountriesCommand) -> tuple[str, int, datetime]:
        return await self._delegate.execute()
