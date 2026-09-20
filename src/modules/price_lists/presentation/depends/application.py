from src.modules.price_lists.presentation.depends.infrastructure import SyncRunRepositoryDep,get_background_repositories,get_background_transaction_factory,get_price_list_lock,get_import_observer,get_source_fetcher,get_source_parser
from src.modules.price_lists.domain.price_list.repository import PriceListRepository
from src.modules.price_lists.domain.offer.repository import OfferRepository
from src.modules.price_lists.domain.sync_run.repository import SyncRunRepository
from src.modules.price_lists.application.sync_run.ports import StagingPort,JobSchedulerPort
from src.modules.shared.application.persistence.unit_of_work_protocol import UnitOfWorkProtocol
from src.modules.shared.presentation.jobs import build_scheduled_job_repository
from dataclasses import dataclass
from typing import Annotated
from fastapi import Depends
from src.modules.price_lists.presentation.depends.infrastructure import (
    PriceListRepositoryDep,
    QueryRepositoryDep,
    ImportOptionsDep,
    SourceFetcherDep,
    SourceParserDep,
    SourceCipherDep,
    CalendarDep,
    IdentifierGeneratorDep,
    JobSchedulerDep,
    get_import_options,
    get_tenant_naming,
    get_source_cipher,
    get_calendar,
    get_identifier_generator,
)
from src.modules.shared.presentation.time.depends import ClockDep, default_clock
from src.modules.price_lists.application.price_list.source_preview import SourcePreview
from src.modules.price_lists.domain.offer.service import OfferService
from src.modules.price_lists.infrastructure.transaction import (
    SqlAlchemyImportTransactionFactory,
)
from src.modules.price_lists.infrastructure.locking import PostgresPriceListLock
from src.modules.price_lists.infrastructure.metrics import PrometheusImportObserver
from src.modules.price_lists.presentation.depends.infrastructure import (
    SqlAlchemyPriceListRepository,
    SqlAlchemyOfferRepository,
    SqlAlchemySyncRunRepository,
    SqlAlchemyStagingRepository,
    ScheduledJobsAdapter,
    HttpRemoteFileFetcher,
    SourceParser,
)
from src.modules.price_lists.application.sync_run.use_case.synchronize_price_list import (
    SynchronizePriceListUseCase,
)
from src.modules.price_lists.application.sync_run.use_case.cleanup_price_list import (
    CleanupPriceListUseCase,
)
from src.modules.price_lists.application.price_list.use_case.activate_price_list import (
    ActivatePriceListUseCase,
)
from src.modules.price_lists.application.price_list.use_case.archive_price_list import (
    ArchivePriceListUseCase,
)
from src.modules.price_lists.application.price_list.use_case.create_price_list import (
    CreatePriceListUseCase,
)
from src.modules.price_lists.application.price_list.use_case.delete_price_list import (
    DeletePriceListUseCase,
)
from src.modules.price_lists.application.price_list.use_case.get_price_list import (
    GetPriceListUseCase,
)
from src.modules.price_lists.application.price_list.use_case.list_price_lists import (
    ListPriceListsUseCase,
)
from src.modules.price_lists.application.price_list.use_case.pause_price_list import (
    PausePriceListUseCase,
)
from src.modules.price_lists.application.price_list.use_case.preview_price_list import (
    PreviewPriceListUseCase,
)
from src.modules.price_lists.application.price_list.use_case.preview_schedule import (
    PreviewScheduleUseCase,
)
from src.modules.price_lists.application.price_list.use_case.restore_price_list import (
    RestorePriceListUseCase,
)
from src.modules.price_lists.application.price_list.use_case.resume_price_list import (
    ResumePriceListUseCase,
)
from src.modules.price_lists.application.price_list.use_case.save_mapping import (
    SaveMappingUseCase,
)
from src.modules.price_lists.application.price_list.use_case.save_schedule import (
    SaveScheduleUseCase,
)
from src.modules.price_lists.application.price_list.use_case.sync_price_list import (
    SyncPriceListUseCase,
)
from src.modules.price_lists.application.price_list.use_case.update_settings import (
    UpdateSettingsUseCase,
)
from src.modules.price_lists.application.offer.use_case.list_offers import (
    ListOffersUseCase,
)
from src.modules.price_lists.application.offer.use_case.offer_history import (
    OfferHistoryUseCase,
)
from src.modules.price_lists.application.sync_run.use_case.list_runs import (
    ListRunsUseCase,
)


def get_source_preview(
    fetcher: SourceFetcherDep,
    parser: SourceParserDep,
    cipher: SourceCipherDep,
    options: ImportOptionsDep,
):
    """Собирает общий ограниченный сценарий preview источника."""
    return SourcePreview(fetcher, parser, cipher, options)


SourcePreviewDep = Annotated[SourcePreview, Depends(get_source_preview)]


def get_command_dependencies(
    repository: PriceListRepositoryDep,
    jobs: JobSchedulerDep,
    calendar: CalendarDep,
    identifiers: IdentifierGeneratorDep,
    cipher: SourceCipherDep,
    preview: SourcePreviewDep,
    clock: ClockDep,
    runs: SyncRunRepositoryDep,
):
    """Собирает порты для HTTP command use cases."""
    return dict(
        repository=repository,
        jobs=jobs,
        calendar=calendar,
        identifiers=identifiers,
        cipher=cipher,
        preview=preview,
        clock=clock,
        runs=runs,
    )


CommandDependenciesDep = Annotated[dict, Depends(get_command_dependencies)]


def get_activate_price_list_use_case(
    dependencies: CommandDependenciesDep,
) -> ActivatePriceListUseCase:
    """Собирает ActivatePriceListUseCase."""
    return ActivatePriceListUseCase(**dependencies)


ActivatePriceListUseCaseDep = Annotated[
    ActivatePriceListUseCase, Depends(get_activate_price_list_use_case)
]


def get_archive_price_list_use_case(
    dependencies: CommandDependenciesDep,
) -> ArchivePriceListUseCase:
    """Собирает ArchivePriceListUseCase."""
    return ArchivePriceListUseCase(**dependencies)


ArchivePriceListUseCaseDep = Annotated[
    ArchivePriceListUseCase, Depends(get_archive_price_list_use_case)
]


def get_create_price_list_use_case(
    dependencies: CommandDependenciesDep,
) -> CreatePriceListUseCase:
    """Собирает CreatePriceListUseCase."""
    return CreatePriceListUseCase(**dependencies)


CreatePriceListUseCaseDep = Annotated[
    CreatePriceListUseCase, Depends(get_create_price_list_use_case)
]


def get_delete_price_list_use_case(
    dependencies: CommandDependenciesDep,
) -> DeletePriceListUseCase:
    """Собирает DeletePriceListUseCase."""
    return DeletePriceListUseCase(**dependencies)


DeletePriceListUseCaseDep = Annotated[
    DeletePriceListUseCase, Depends(get_delete_price_list_use_case)
]


def get_get_price_list_use_case(
    repository: PriceListRepositoryDep,
) -> GetPriceListUseCase:
    """Собирает GetPriceListUseCase."""
    return GetPriceListUseCase(repository)


GetPriceListUseCaseDep = Annotated[
    GetPriceListUseCase, Depends(get_get_price_list_use_case)
]


def get_list_price_lists_use_case(
    repository: QueryRepositoryDep,
) -> ListPriceListsUseCase:
    """Собирает ListPriceListsUseCase."""
    return ListPriceListsUseCase(repository)


ListPriceListsUseCaseDep = Annotated[
    ListPriceListsUseCase, Depends(get_list_price_lists_use_case)
]


def get_pause_price_list_use_case(
    dependencies: CommandDependenciesDep,
) -> PausePriceListUseCase:
    """Собирает PausePriceListUseCase."""
    return PausePriceListUseCase(**dependencies)


PausePriceListUseCaseDep = Annotated[
    PausePriceListUseCase, Depends(get_pause_price_list_use_case)
]


def get_preview_price_list_use_case(
    repository: PriceListRepositoryDep, preview: SourcePreviewDep
) -> PreviewPriceListUseCase:
    """Собирает PreviewPriceListUseCase."""
    return PreviewPriceListUseCase(repository, preview)


PreviewPriceListUseCaseDep = Annotated[
    PreviewPriceListUseCase, Depends(get_preview_price_list_use_case)
]


def get_preview_schedule_use_case(
    calendar: CalendarDep, clock: ClockDep
) -> PreviewScheduleUseCase:
    """Собирает PreviewScheduleUseCase."""
    return PreviewScheduleUseCase(calendar, clock)


PreviewScheduleUseCaseDep = Annotated[
    PreviewScheduleUseCase, Depends(get_preview_schedule_use_case)
]


def get_restore_price_list_use_case(
    dependencies: CommandDependenciesDep,
) -> RestorePriceListUseCase:
    """Собирает RestorePriceListUseCase."""
    return RestorePriceListUseCase(**dependencies)


RestorePriceListUseCaseDep = Annotated[
    RestorePriceListUseCase, Depends(get_restore_price_list_use_case)
]


def get_resume_price_list_use_case(
    dependencies: CommandDependenciesDep,
) -> ResumePriceListUseCase:
    """Собирает ResumePriceListUseCase."""
    return ResumePriceListUseCase(**dependencies)


ResumePriceListUseCaseDep = Annotated[
    ResumePriceListUseCase, Depends(get_resume_price_list_use_case)
]


def get_save_mapping_use_case(
    dependencies: CommandDependenciesDep,
) -> SaveMappingUseCase:
    """Собирает SaveMappingUseCase."""
    return SaveMappingUseCase(**dependencies)


SaveMappingUseCaseDep = Annotated[
    SaveMappingUseCase, Depends(get_save_mapping_use_case)
]


def get_save_schedule_use_case(
    dependencies: CommandDependenciesDep,
) -> SaveScheduleUseCase:
    """Собирает SaveScheduleUseCase."""
    return SaveScheduleUseCase(**dependencies)


SaveScheduleUseCaseDep = Annotated[
    SaveScheduleUseCase, Depends(get_save_schedule_use_case)
]


def get_sync_price_list_use_case(
    dependencies: CommandDependenciesDep,
) -> SyncPriceListUseCase:
    """Собирает SyncPriceListUseCase."""
    return SyncPriceListUseCase(**dependencies)


SyncPriceListUseCaseDep = Annotated[
    SyncPriceListUseCase, Depends(get_sync_price_list_use_case)
]


def get_update_settings_use_case(
    dependencies: CommandDependenciesDep,
) -> UpdateSettingsUseCase:
    """Собирает UpdateSettingsUseCase."""
    return UpdateSettingsUseCase(**dependencies)


UpdateSettingsUseCaseDep = Annotated[
    UpdateSettingsUseCase, Depends(get_update_settings_use_case)
]


def get_list_offers_use_case(repository: QueryRepositoryDep) -> ListOffersUseCase:
    """Собирает ListOffersUseCase."""
    return ListOffersUseCase(repository)


ListOffersUseCaseDep = Annotated[ListOffersUseCase, Depends(get_list_offers_use_case)]


def get_offer_history_use_case(repository: QueryRepositoryDep) -> OfferHistoryUseCase:
    """Собирает OfferHistoryUseCase."""
    return OfferHistoryUseCase(repository)


OfferHistoryUseCaseDep = Annotated[
    OfferHistoryUseCase, Depends(get_offer_history_use_case)
]


def get_list_runs_use_case(repository: QueryRepositoryDep) -> ListRunsUseCase:
    """Собирает ListRunsUseCase."""
    return ListRunsUseCase(repository)


ListRunsUseCaseDep = Annotated[ListRunsUseCase, Depends(get_list_runs_use_case)]


@dataclass(slots=True)
class ImportComponents:
    """Компоненты фоновой UoW, собранные в presentation."""

    prices: PriceListRepository
    offers: OfferRepository
    runs: SyncRunRepository
    staging: StagingPort
    jobs: JobSchedulerPort
    offer_service: OfferService
    uow: UnitOfWorkProtocol

    async def commit(self):
        """Фиксирует текущую UoW."""
        await self.uow.commit()

    async def rollback(self):
        """Откатывает текущую UoW."""
        await self.uow.rollback()


def get_background_transactions(session_factory, *, options=None, clock=None):
    """Собирает domain service над repository каждой фоновой UoW."""
    options=options or get_import_options();clock=clock or default_clock
    def assemble(uow):
        ports=get_background_repositories(uow,options,clock)
        return ImportComponents(**ports,offer_service=OfferService(ports['offers'],clock),uow=uow)
    return get_background_transaction_factory(session_factory,assemble)


def get_synchronize_price_list_use_case(session_factory):
    """Собирает CRON use case без HTTP dependency resolution."""
    options=get_import_options()
    return SynchronizePriceListUseCase(get_background_transactions(session_factory,options=options),get_source_fetcher(options),get_source_parser(options),get_source_cipher(),get_calendar(),get_identifier_generator(),get_price_list_lock(session_factory),default_clock,options,get_import_observer())


def get_cleanup_price_list_use_case(session_factory):
    """Собирает сценарий обслуживания staging."""
    return CleanupPriceListUseCase(get_background_transactions(session_factory),default_clock,get_import_options())

__all__=[name for name in globals() if name.startswith('get_') or name.endswith('Dep')]
