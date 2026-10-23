from src.modules.catalog.application.catalog_item.creation_service import (
    CatalogItemCreationService,
)
from src.modules.catalog.infrastructure.catalog_item.sku import SqlAlchemyCatalogItemSku
from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.catalog.presentation.depends.common import (
    MutationLockDep,
    LocalesDep,
    SanitizerDep,
)
from src.modules.catalog.domain.catalog_item.repository import (
    CatalogItemRepositoryProtocol,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.repository import (
    SqlAlchemyCatalogItemRepository,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.query_repository import (
    SqlAlchemyCatalogItemQueryRepository,
)
from src.modules.catalog.application.catalog_item.port.query_repository import (
    CatalogItemQueryRepositoryProtocol,
)
from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.catalog.application.catalog_item.port.content_schema import (
    CatalogItemContentSchemaPort,
)
from src.modules.catalog.infrastructure.catalog_item.content_schema import (
    SqlAlchemyProductTypeSchemas,
)
from src.modules.catalog.application.catalog_item.port.files import (
    CatalogImageFilesPort,
)
from src.modules.catalog.infrastructure.catalog_item.files import FilesCatalogImages
from src.modules.files.infrastructure.assembly import build_files_handlers
from src.modules.catalog.application.port.currencies import CurrencyPort
from src.modules.catalog.infrastructure.currencies import ReferenceDataCurrencies
from src.modules.reference_data.presentation.depends import ValidateCurrencyHandlerDep


def get_item_repository(uow: UoWDep) -> CatalogItemRepositoryProtocol:
    """Собирает порт item_repository конкретного процесса."""
    return SqlAlchemyCatalogItemRepository(uow.session)


ItemRepositoryDep = Annotated[
    CatalogItemRepositoryProtocol, Depends(get_item_repository)
]


def get_schemas(uow: UoWDep) -> CatalogItemContentSchemaPort:
    """Собирает порт schemas конкретного процесса."""
    return SqlAlchemyProductTypeSchemas(uow.session)


SchemasDep = Annotated[CatalogItemContentSchemaPort, Depends(get_schemas)]


def get_currencies(handler: ValidateCurrencyHandlerDep) -> CurrencyPort:
    """Собирает порт currencies конкретного процесса."""
    return ReferenceDataCurrencies(handler)


CurrenciesDep = Annotated[CurrencyPort, Depends(get_currencies)]


def get_files(uow: UoWDep) -> CatalogImageFilesPort:
    """Собирает публичные Files handlers на сессии Catalog UoW."""
    handlers = build_files_handlers(uow.session)
    return FilesCatalogImages(handlers.upload, handlers.content, handlers.lock_ready)


FilesDep = Annotated[CatalogImageFilesPort, Depends(get_files)]


def get_queries(uow: UoWDep) -> CatalogItemQueryRepositoryProtocol:
    """Собирает read порт на UoW, настроенном внешней зависимостью роутера."""
    return SqlAlchemyCatalogItemQueryRepository(uow.session)


QueriesDep = Annotated[CatalogItemQueryRepositoryProtocol, Depends(get_queries)]


def get_mutations(
    repository: ItemRepositoryDep, lock: MutationLockDep
) -> CatalogItemMutationService:
    """Собирает координатор mutations на портах общей session."""
    return CatalogItemMutationService(repository, lock)


MutationsDep = Annotated[CatalogItemMutationService, Depends(get_mutations)]
from src.modules.catalog.application.catalog_item.command.create_catalog_item.handler import (
    CreateCatalogItemHandler,
)


def get_create_catalog_item_handler(
    repository: ItemRepositoryDep,
    schemas: SchemasDep,
    clock: ClockDep,
    uuid: UuidDep,
    locales: LocalesDep,
    currencies: CurrenciesDep,
    sanitizer: SanitizerDep,
    files: FilesDep,
    uow: UoWDep,
) -> CreateCatalogItemHandler:
    """Собирает отдельный handler сценария create_catalog_item."""
    return CreateCatalogItemHandler(
        repository,
        CatalogItemCreationService(
            schemas,
            locales,
            currencies,
            SqlAlchemyCatalogItemSku(uow.session),
            sanitizer,
            files,
            clock,
            uuid,
        ),
    )


CreateCatalogItemHandlerDep = Annotated[
    CreateCatalogItemHandler, Depends(get_create_catalog_item_handler)
]
from src.modules.catalog.application.catalog_item.command.delete_catalog_item.handler import (
    DeleteCatalogItemHandler,
)


def get_delete_catalog_item_handler(
    mutations: MutationsDep, repository: ItemRepositoryDep
) -> DeleteCatalogItemHandler:
    """Собирает отдельный handler сценария delete_catalog_item."""
    return DeleteCatalogItemHandler(mutations=mutations, repository=repository)


DeleteCatalogItemHandlerDep = Annotated[
    DeleteCatalogItemHandler, Depends(get_delete_catalog_item_handler)
]
from src.modules.catalog.application.catalog_item.command.upload_catalog_item_image.handler import (
    UploadCatalogItemImageHandler,
)


def get_upload_catalog_item_image_handler(
    mutations: MutationsDep,
    files: FilesDep,
    locales: LocalesDep,
    clock: ClockDep,
    uuid: UuidDep,
) -> UploadCatalogItemImageHandler:
    """Собирает отдельный handler сценария upload_catalog_item_image."""
    return UploadCatalogItemImageHandler(
        mutations=mutations, files=files, locales=locales, clock=clock, uuid=uuid
    )


UploadCatalogItemImageHandlerDep = Annotated[
    UploadCatalogItemImageHandler, Depends(get_upload_catalog_item_image_handler)
]
from src.modules.catalog.application.catalog_item.query.get_catalog_item.handler import (
    GetCatalogItemHandler,
)


def get_get_catalog_item_handler(
    repository: QueriesDep, clock: ClockDep
) -> GetCatalogItemHandler:
    """Собирает отдельный handler сценария get_catalog_item."""
    return GetCatalogItemHandler(repository=repository, clock=clock)


GetCatalogItemHandlerDep = Annotated[
    GetCatalogItemHandler, Depends(get_get_catalog_item_handler)
]
from src.modules.catalog.application.catalog_item.query.get_catalog_item_image_content.handler import (
    GetCatalogItemImageContentHandler,
)


def get_get_catalog_item_image_content_handler(
    repository: QueriesDep, files: FilesDep, clock: ClockDep
) -> GetCatalogItemImageContentHandler:
    """Собирает отдельный handler сценария get_catalog_item_image_content."""
    return GetCatalogItemImageContentHandler(
        repository=repository, files=files, clock=clock
    )


GetCatalogItemImageContentHandlerDep = Annotated[
    GetCatalogItemImageContentHandler,
    Depends(get_get_catalog_item_image_content_handler),
]


from src.modules.catalog.application.catalog_item.query.list_catalog_items.handler import (
    ListCatalogItemsHandler,
)


def get_list_catalog_items_handler(
    repository: QueriesDep, clock: ClockDep
) -> ListCatalogItemsHandler:
    """Собирает отдельный handler сценария list_catalog_items."""
    return ListCatalogItemsHandler(repository=repository, clock=clock)


ListCatalogItemsHandlerDep = Annotated[
    ListCatalogItemsHandler, Depends(get_list_catalog_items_handler)
]
from src.modules.catalog.application.catalog_item.command.update_catalog_item.handler import (
    UpdateCatalogItemHandler,
)


def get_update_catalog_item_handler(
    mutations: MutationsDep,
    clock: ClockDep,
    locales: LocalesDep,
    schemas: SchemasDep,
    sanitizer: SanitizerDep,
    currencies: CurrenciesDep,
    files: FilesDep,
) -> UpdateCatalogItemHandler:
    """Собирает единый сценарий изменения на портах общего UoW."""
    return UpdateCatalogItemHandler(
        mutations, clock, locales, schemas, sanitizer, currencies, files
    )


UpdateCatalogItemHandlerDep = Annotated[
    UpdateCatalogItemHandler, Depends(get_update_catalog_item_handler)
]
