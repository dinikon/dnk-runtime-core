from src.modules.shared.presentation.jobs import build_scheduled_job_repository
from dataclasses import fields
from typing import Annotated
from fastapi import Depends
from src.config import dnk_config
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.price_lists.application.sync_run.options import ImportOptions
from src.modules.price_lists.infrastructure.persistence.price_list_repository import (
    SqlAlchemyPriceListRepository,
)
from src.modules.price_lists.infrastructure.persistence.offer_repository import (
    SqlAlchemyOfferRepository,
)
from src.modules.price_lists.infrastructure.persistence.sync_run_repository import (
    SqlAlchemySyncRunRepository,
)
from src.modules.price_lists.infrastructure.persistence.staging_repository import (
    SqlAlchemyStagingRepository,
)
from src.modules.price_lists.infrastructure.persistence.query_repository import (
    SqlAlchemyPriceListQueryRepository,
)
from src.modules.price_lists.infrastructure.source.fetcher import HttpRemoteFileFetcher
from src.modules.price_lists.infrastructure.source.parser import SourceParser
from src.modules.price_lists.infrastructure.source.secret import SourceUrlCipher
from src.modules.price_lists.infrastructure.calendar import (
    CronCalendar,
    IdentifierGenerator,
)
from src.modules.price_lists.infrastructure.jobs import ScheduledJobsAdapter
from src.modules.shared.presentation.time.depends import ClockDep


def get_import_options() -> ImportOptions:
    """Передаёт настройки в immutable application contract."""
    return ImportOptions(
        **{
            field.name: getattr(dnk_config.PRICE_LISTS, field.name)
            for field in fields(ImportOptions)
        }
    )


ImportOptionsDep = Annotated[ImportOptions, Depends(get_import_options)]


def get_tenant_naming() -> TenantSchemaNaming:
    """Выбирает общую стратегию tenant schema."""
    return TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)


TenantNamingDep = Annotated[TenantSchemaNaming, Depends(get_tenant_naming)]


def get_price_list_repository(
    uow: UoWDep, naming: TenantNamingDep, options: ImportOptionsDep
):
    """Создаёт repository на shared request UoW."""
    return SqlAlchemyPriceListRepository(uow.session, naming, options)


PriceListRepositoryDep = Annotated[
    SqlAlchemyPriceListRepository, Depends(get_price_list_repository)
]


def get_query_repository(
    uow: UoWDep, naming: TenantNamingDep, options: ImportOptionsDep
):
    """Создаёт типизированный query adapter."""
    return SqlAlchemyPriceListQueryRepository(uow.session, naming, options)


QueryRepositoryDep = Annotated[
    SqlAlchemyPriceListQueryRepository, Depends(get_query_repository)
]


def get_identifier_generator():
    """Создаёт генератор доменных идентификаторов."""
    return IdentifierGenerator()


IdentifierGeneratorDep = Annotated[
    IdentifierGenerator, Depends(get_identifier_generator)
]


def get_calendar():
    """Создаёт адаптер календарного расписания."""
    return CronCalendar()


CalendarDep = Annotated[CronCalendar, Depends(get_calendar)]


def get_source_cipher():
    """Создаёт адаптер защиты URL с явным ключом конфигурации."""
    return SourceUrlCipher(dnk_config.PRICE_LISTS.source_encryption_key)


SourceCipherDep = Annotated[SourceUrlCipher, Depends(get_source_cipher)]


def get_source_fetcher(options: ImportOptionsDep):
    """Создаёт ограниченный streaming fetcher."""
    return HttpRemoteFileFetcher(options=options)


SourceFetcherDep = Annotated[HttpRemoteFileFetcher, Depends(get_source_fetcher)]


def get_source_parser(options: ImportOptionsDep):
    """Создаёт потоковые adapters для всех форматов."""
    return SourceParser(options)


SourceParserDep = Annotated[SourceParser, Depends(get_source_parser)]


def get_job_scheduler(
    uow: UoWDep, clock: ClockDep, identifiers: IdentifierGeneratorDep
):
    """Создаёт scheduled-jobs adapter на той же request UoW."""
    return ScheduledJobsAdapter(build_scheduled_job_repository(uow.session), clock, identifiers)


JobSchedulerDep = Annotated[ScheduledJobsAdapter, Depends(get_job_scheduler)]

__all__ = [
    name for name in globals() if name.startswith("get_") or name.endswith("Dep")
]
