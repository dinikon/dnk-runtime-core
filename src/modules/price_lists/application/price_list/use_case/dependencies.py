from src.modules.price_lists.domain.sync_run.repository import SyncRunRepository
from src.modules.price_lists.domain.price_list.repository import PriceListRepository
from src.modules.price_lists.application.sync_run.ports import (
    JobSchedulerPort,
    CalendarPort,
    IdentifierPort,
    SourceCipher,
)
from src.modules.price_lists.application.price_list.source_preview import SourcePreview
from src.modules.shared.domain.time.clock_port import ClockPort


class PriceListUseCase:
    """Общие внедрённые порты command-сценариев прайса."""

    def __init__(
        self,
        repository: PriceListRepository,
        jobs: JobSchedulerPort,
        calendar: CalendarPort,
        identifiers: IdentifierPort,
        cipher: SourceCipher,
        preview: SourcePreview,
        clock: ClockPort,
        runs: SyncRunRepository,
    ):
        self.repository = repository
        self.jobs = jobs
        self.calendar = calendar
        self.identifiers = identifiers
        self.cipher = cipher
        self.preview = preview
        self.clock = clock
        self.runs = runs


__all__ = ["PriceListUseCase"]
