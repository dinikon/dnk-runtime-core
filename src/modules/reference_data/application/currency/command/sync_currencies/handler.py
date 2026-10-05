from datetime import datetime

from src.modules.reference_data.application.currency.command.sync_currencies.command import (
    SyncCurrenciesCommand,
)
from src.modules.reference_data.application.port.catalog import (
    CatalogRepositoryPort,
    SourcePort,
)
from src.modules.reference_data.application.sync.handler import SyncReferenceDataHandler
from src.modules.reference_data.domain.currency.record import Currency
from src.modules.shared.domain.time.clock_port import ClockPort


class SyncCurrenciesHandler:
    def __init__(
        self,
        source: SourcePort[Currency],
        repository: CatalogRepositoryPort,
        clock: ClockPort,
    ):
        self._delegate = SyncReferenceDataHandler(
            "currencies", source, repository, clock
        )

    async def execute(
        self, command: SyncCurrenciesCommand
    ) -> tuple[str, int, datetime]:
        return await self._delegate.execute()
