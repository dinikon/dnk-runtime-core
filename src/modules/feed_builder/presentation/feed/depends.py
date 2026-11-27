from typing import Annotated

from src.modules.shared.infrastructure.content.rich_text import sanitize_rich_text
from fastapi import Depends
from src.modules.feed_builder.domain.feed.repository import FeedRepositoryProtocol
from src.modules.feed_builder.application.feed.port.query_repository import (
    FeedQueryRepositoryProtocol,
)
from src.modules.feed_builder.infrastructure.feed.persistence.repository import (
    SqlAlchemyFeedRepository,
)
from src.modules.feed_builder.infrastructure.feed.persistence.query_repository import (
    SqlAlchemyFeedQueryRepository,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.feed_builder.application.feed.port.settings_repository import (
    FeedSettingsRepositoryProtocol,
)
from src.modules.feed_builder.application.feed.command.create_feed.handler import (
    CreateFeedHandler,
)
from src.modules.feed_builder.application.feed.command.update_feed.handler import (
    UpdateFeedHandler,
)
from src.modules.feed_builder.application.feed.command.archive_feed.handler import (
    ArchiveFeedHandler,
)
from src.modules.feed_builder.application.feed.query.get_feed.handler import (
    GetFeedHandler,
)
from src.modules.feed_builder.application.feed.query.list_feeds.handler import (
    ListFeedsHandler,
)
from src.modules.feed_builder.application.feed.port.schema_locales import (
    SchemaLocalesPort,
)
from src.modules.feed_builder.infrastructure.feed.reference_data.schema_locales import (
    ReferenceDataSchemaLocales,
)
from src.modules.reference_data.presentation.depends import CatalogRepositoryDep
from src.modules.feed_builder.application.feed.command.save_feed_schema_draft.handler import (
    SaveFeedSchemaDraftHandler,
)
from src.modules.feed_builder.application.feed.query.get_feed_schema.handler import (
    GetFeedSchemaHandler,
)
from src.modules.feed_builder.application.feed.query.list_field_types.handler import (
    ListFieldTypesHandler,
)
from src.modules.feed_builder.application.feed.query.list_source_paths.handler import (
    ListSourcePathsHandler,
)
from src.modules.feed_builder.application.feed.query.list_transforms.handler import (
    ListTransformsHandler,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.calculation_reader import (
    SqlAlchemyCatalogCalculationReader,
)
from src.modules.feed_builder.infrastructure.feed.catalog.calculation_product import (
    CatalogCalculationProductReader,
)
from src.modules.feed_builder.application.feed.port.calculation_product import (
    CalculationProductReaderProtocol,
)
from src.modules.feed_builder.application.feed.query.preview_field_calculation.handler import (
    PreviewFieldCalculationHandler,
)
from src.modules.feed_builder.application.feed.query.list_calculation_parameters.handler import (
    ListCalculationParametersHandler,
)
from src.modules.feed_builder.application.feed.query.list_calculation_operations.handler import (
    ListCalculationOperationsHandler,
)


def get_feed_repository(uow: UoWDep) -> FeedRepositoryProtocol:
    """Создаёт репозиторий записи на общей сессии UoW."""
    return SqlAlchemyFeedRepository(uow.session)


def get_feed_query_repository(uow: UoWDep) -> FeedQueryRepositoryProtocol:
    """Создаёт отдельный репозиторий проекций на той же сессии."""
    return SqlAlchemyFeedQueryRepository(uow.session)


FeedRepositoryDep = Annotated[FeedRepositoryProtocol, Depends(get_feed_repository)]
FeedQueryRepositoryDep = Annotated[
    FeedQueryRepositoryProtocol, Depends(get_feed_query_repository)
]


def get_create_feed_handler(
    repository: FeedRepositoryDep, clock: ClockDep, uuid_generator: UuidDep
) -> CreateFeedHandler:
    """Собирает сценарий create_feed из контрактов и общих зависимостей."""
    return CreateFeedHandler(repository, clock, uuid_generator)


CreateFeedHandlerDep = Annotated[CreateFeedHandler, Depends(get_create_feed_handler)]


def get_feed_settings_repository(uow: UoWDep) -> FeedSettingsRepositoryProtocol:
    """Собирает порт управления фидом на общей tenant-сессии."""
    return SqlAlchemyFeedRepository(uow.session)


FeedSettingsRepositoryDep = Annotated[
    FeedSettingsRepositoryProtocol, Depends(get_feed_settings_repository)
]


def get_update_feed_handler(
    repository: FeedSettingsRepositoryDep, clock: ClockDep
) -> UpdateFeedHandler:
    """Собирает сценарий update_feed из контрактов и общих зависимостей."""
    return UpdateFeedHandler(repository, clock)


UpdateFeedHandlerDep = Annotated[UpdateFeedHandler, Depends(get_update_feed_handler)]


def get_archive_feed_handler(
    repository: FeedSettingsRepositoryDep, clock: ClockDep
) -> ArchiveFeedHandler:
    """Собирает сценарий archive_feed из контрактов и общих зависимостей."""
    return ArchiveFeedHandler(repository, clock)


ArchiveFeedHandlerDep = Annotated[ArchiveFeedHandler, Depends(get_archive_feed_handler)]


def get_get_feed_handler(repository: FeedQueryRepositoryDep) -> GetFeedHandler:
    """Собирает сценарий get_feed из контрактов и общих зависимостей."""
    return GetFeedHandler(repository)


GetFeedHandlerDep = Annotated[GetFeedHandler, Depends(get_get_feed_handler)]


def get_list_feeds_handler(repository: FeedQueryRepositoryDep) -> ListFeedsHandler:
    """Собирает сценарий list_feeds из контрактов и общих зависимостей."""
    return ListFeedsHandler(repository)


ListFeedsHandlerDep = Annotated[ListFeedsHandler, Depends(get_list_feeds_handler)]


def get_schema_locales(catalog: CatalogRepositoryDep) -> SchemaLocalesPort:
    """Подключает owner-порт справочника к общему UoW без чужих SQL imports."""
    return ReferenceDataSchemaLocales(catalog)


SchemaLocalesDep = Annotated[SchemaLocalesPort, Depends(get_schema_locales)]


def get_save_feed_schema_draft_handler(
    repository: FeedRepositoryDep, clock: ClockDep, locales: SchemaLocalesDep
) -> SaveFeedSchemaDraftHandler:
    """Собирает атомарное сохранение рабочей схемы на существующих портах."""
    return SaveFeedSchemaDraftHandler(repository, clock, locales, sanitize_rich_text)


SaveFeedSchemaDraftHandlerDep = Annotated[
    SaveFeedSchemaDraftHandler, Depends(get_save_feed_schema_draft_handler)
]


def get_feed_schema_handler(repository: FeedQueryRepositoryDep) -> GetFeedSchemaHandler:
    """Собирает чтение проекции схемы без write repository."""
    return GetFeedSchemaHandler(repository)


GetFeedSchemaHandlerDep = Annotated[
    GetFeedSchemaHandler, Depends(get_feed_schema_handler)
]


def get_list_field_types_handler(locales: SchemaLocalesDep) -> ListFieldTypesHandler:
    """Собирает реестр типов с доступными локалями."""
    return ListFieldTypesHandler(locales)


ListFieldTypesHandlerDep = Annotated[
    ListFieldTypesHandler, Depends(get_list_field_types_handler)
]


def get_list_source_paths_handler() -> ListSourcePathsHandler:
    """Собирает закрытый реестр прямых источников."""
    return ListSourcePathsHandler()


ListSourcePathsHandlerDep = Annotated[
    ListSourcePathsHandler, Depends(get_list_source_paths_handler)
]


def get_list_transforms_handler() -> ListTransformsHandler:
    """Собирает реестр определений преобразований."""
    return ListTransformsHandler()


ListTransformsHandlerDep = Annotated[
    ListTransformsHandler, Depends(get_list_transforms_handler)
]


def get_calculation_products(uow: UoWDep) -> CalculationProductReaderProtocol:
    """Собирает Catalog owner-reader и адаптер на общей tenant-сессии."""
    return CatalogCalculationProductReader(
        SqlAlchemyCatalogCalculationReader(uow.session)
    )


CalculationProductsDep = Annotated[
    CalculationProductReaderProtocol, Depends(get_calculation_products)
]


def get_preview_field_calculation_handler(
    repository: FeedQueryRepositoryDep,
    products: CalculationProductsDep,
    clock: ClockDep,
) -> PreviewFieldCalculationHandler:
    """Собирает read-only preview без write repository, jobs или отдельного UoW."""
    return PreviewFieldCalculationHandler(repository, products, clock)


PreviewFieldCalculationHandlerDep = Annotated[
    PreviewFieldCalculationHandler, Depends(get_preview_field_calculation_handler)
]


def get_list_calculation_parameters_handler() -> ListCalculationParametersHandler:
    """Собирает реестр подключённых параметров."""
    return ListCalculationParametersHandler()


ListCalculationParametersHandlerDep = Annotated[
    ListCalculationParametersHandler, Depends(get_list_calculation_parameters_handler)
]


def get_list_calculation_operations_handler() -> ListCalculationOperationsHandler:
    """Собирает реестр закрытых операций вычислителя."""
    return ListCalculationOperationsHandler()


ListCalculationOperationsHandlerDep = Annotated[
    ListCalculationOperationsHandler, Depends(get_list_calculation_operations_handler)
]
