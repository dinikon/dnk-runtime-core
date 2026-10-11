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
from src.modules.catalog.application.catalog_item.structure_service import (
    CatalogItemStructureService,
)
from src.modules.catalog.infrastructure.catalog_item.owner_lookup import (
    SqlAlchemyCatalogItemOwnerLookup,
)
from src.modules.catalog.application.catalog_item.port.attribute_definitions import (
    AttributeDefinitionsPort,
)
from src.modules.catalog.infrastructure.catalog_item.attribute_definitions import (
    SqlAlchemyAttributeDefinitions,
)
from src.modules.catalog.application.catalog_item.port.classification_references import (
    ClassificationReferencesPort,
)
from src.modules.catalog.infrastructure.catalog_item.classification_references import (
    SqlAlchemyClassificationReferences,
)
from src.modules.catalog.application.catalog_item.port.content_schema import (
    CatalogItemContentSchemaPort,
)
from src.modules.catalog.infrastructure.catalog_item.content_schema import (
    SqlAlchemyDefaultContentSchema,
)
from src.modules.catalog.application.catalog_item.port.usage import CatalogItemUsagePort
from src.modules.catalog.infrastructure.catalog_item.usage import (
    UnboundCatalogItemUsage,
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


def get_definitions(uow: UoWDep) -> AttributeDefinitionsPort:
    """Собирает порт definitions конкретного процесса."""
    return SqlAlchemyAttributeDefinitions(uow.session)


DefinitionsDep = Annotated[AttributeDefinitionsPort, Depends(get_definitions)]


def get_references(uow: UoWDep) -> ClassificationReferencesPort:
    """Собирает порт references конкретного процесса."""
    return SqlAlchemyClassificationReferences(uow.session)


ReferencesDep = Annotated[ClassificationReferencesPort, Depends(get_references)]


def get_schemas(uow: UoWDep) -> CatalogItemContentSchemaPort:
    """Собирает порт schemas конкретного процесса."""
    return SqlAlchemyDefaultContentSchema(uow.session)


SchemasDep = Annotated[CatalogItemContentSchemaPort, Depends(get_schemas)]


def get_usage() -> CatalogItemUsagePort:
    """Собирает порт usage конкретного процесса."""
    return UnboundCatalogItemUsage()


UsageDep = Annotated[CatalogItemUsagePort, Depends(get_usage)]


def get_currencies(handler: ValidateCurrencyHandlerDep) -> CurrencyPort:
    """Собирает порт currencies конкретного процесса."""
    return ReferenceDataCurrencies(handler)


CurrenciesDep = Annotated[CurrencyPort, Depends(get_currencies)]


def get_files(uow: UoWDep) -> CatalogImageFilesPort:
    """Собирает публичные Files handlers на сессии Catalog UoW."""
    handlers = build_files_handlers(uow.session)
    return FilesCatalogImages(handlers.upload, handlers.content)


FilesDep = Annotated[CatalogImageFilesPort, Depends(get_files)]


def get_queries(uow: UoWDep) -> CatalogItemQueryRepositoryProtocol:
    """Собирает read порт на UoW, настроенном внешней зависимостью роутера."""
    return SqlAlchemyCatalogItemQueryRepository(uow.session)


QueriesDep = Annotated[CatalogItemQueryRepositoryProtocol, Depends(get_queries)]


def get_mutations(
    repository: ItemRepositoryDep, lock: MutationLockDep, uow: UoWDep
) -> CatalogItemMutationService:
    """Собирает координатор mutations на портах общей session."""
    return CatalogItemMutationService(
        repository, SqlAlchemyCatalogItemOwnerLookup(uow.session), lock
    )


MutationsDep = Annotated[CatalogItemMutationService, Depends(get_mutations)]


def get_structures(
    definitions: DefinitionsDep, uuid: UuidDep
) -> CatalogItemStructureService:
    """Собирает координатор structures на портах общей session."""
    return CatalogItemStructureService(definitions, uuid)


StructuresDep = Annotated[CatalogItemStructureService, Depends(get_structures)]

from src.modules.catalog.application.catalog_item.command.change_catalog_item_kind.handler import (
    ChangeCatalogItemKindHandler,
)


def get_change_catalog_item_kind_handler(
    mutations: MutationsDep, clock: ClockDep, structures: StructuresDep, usage: UsageDep
) -> ChangeCatalogItemKindHandler:
    """Собирает отдельный handler сценария change_catalog_item_kind."""
    return ChangeCatalogItemKindHandler(
        mutations=mutations, clock=clock, structures=structures, usage=usage
    )


ChangeCatalogItemKindHandlerDep = Annotated[
    ChangeCatalogItemKindHandler, Depends(get_change_catalog_item_kind_handler)
]

from src.modules.catalog.application.catalog_item.command.create_simple_catalog_item.handler import (
    CreateSimpleCatalogItemHandler,
)


def get_create_simple_catalog_item_handler(
    repository: ItemRepositoryDep,
    lock: MutationLockDep,
    clock: ClockDep,
    uuid: UuidDep,
) -> CreateSimpleCatalogItemHandler:
    """Собирает отдельный handler сценария create_simple_catalog_item."""
    return CreateSimpleCatalogItemHandler(
        repository=repository, lock=lock, clock=clock, uuid=uuid
    )


CreateSimpleCatalogItemHandlerDep = Annotated[
    CreateSimpleCatalogItemHandler, Depends(get_create_simple_catalog_item_handler)
]

from src.modules.catalog.application.catalog_item.command.create_variable_catalog_item.handler import (
    CreateVariableCatalogItemHandler,
)


def get_create_variable_catalog_item_handler(
    repository: ItemRepositoryDep,
    lock: MutationLockDep,
    clock: ClockDep,
    uuid: UuidDep,
    structures: StructuresDep,
) -> CreateVariableCatalogItemHandler:
    """Собирает отдельный handler сценария create_variable_catalog_item."""
    return CreateVariableCatalogItemHandler(
        repository=repository, lock=lock, clock=clock, uuid=uuid, structures=structures
    )


CreateVariableCatalogItemHandlerDep = Annotated[
    CreateVariableCatalogItemHandler, Depends(get_create_variable_catalog_item_handler)
]

from src.modules.catalog.application.catalog_item.command.delete_catalog_item.handler import (
    DeleteCatalogItemHandler,
)


def get_delete_catalog_item_handler(
    mutations: MutationsDep, repository: ItemRepositoryDep, usage: UsageDep
) -> DeleteCatalogItemHandler:
    """Собирает отдельный handler сценария delete_catalog_item."""
    return DeleteCatalogItemHandler(
        mutations=mutations, repository=repository, usage=usage
    )


DeleteCatalogItemHandlerDep = Annotated[
    DeleteCatalogItemHandler, Depends(get_delete_catalog_item_handler)
]

from src.modules.catalog.application.catalog_item.command.delete_catalog_item_content.handler import (
    DeleteCatalogItemContentHandler,
)


def get_delete_catalog_item_content_handler(
    mutations: MutationsDep, clock: ClockDep
) -> DeleteCatalogItemContentHandler:
    """Собирает отдельный handler сценария delete_catalog_item_content."""
    return DeleteCatalogItemContentHandler(mutations=mutations, clock=clock)


DeleteCatalogItemContentHandlerDep = Annotated[
    DeleteCatalogItemContentHandler, Depends(get_delete_catalog_item_content_handler)
]

from src.modules.catalog.application.catalog_item.command.delete_catalog_item_gallery.handler import (
    DeleteCatalogItemGalleryHandler,
)


def get_delete_catalog_item_gallery_handler(
    mutations: MutationsDep, clock: ClockDep
) -> DeleteCatalogItemGalleryHandler:
    """Собирает отдельный handler сценария delete_catalog_item_gallery."""
    return DeleteCatalogItemGalleryHandler(mutations=mutations, clock=clock)


DeleteCatalogItemGalleryHandlerDep = Annotated[
    DeleteCatalogItemGalleryHandler, Depends(get_delete_catalog_item_gallery_handler)
]

from src.modules.catalog.application.catalog_item.command.put_catalog_item_content.handler import (
    PutCatalogItemContentHandler,
)


def get_put_catalog_item_content_handler(
    mutations: MutationsDep,
    clock: ClockDep,
    locales: LocalesDep,
    schemas: SchemasDep,
    sanitizer: SanitizerDep,
) -> PutCatalogItemContentHandler:
    """Собирает отдельный handler сценария put_catalog_item_content."""
    return PutCatalogItemContentHandler(
        mutations=mutations,
        clock=clock,
        locales=locales,
        schemas=schemas,
        sanitizer=sanitizer,
    )


PutCatalogItemContentHandlerDep = Annotated[
    PutCatalogItemContentHandler, Depends(get_put_catalog_item_content_handler)
]

from src.modules.catalog.application.catalog_item.command.replace_catalog_item_gallery.handler import (
    ReplaceCatalogItemGalleryHandler,
)


def get_replace_catalog_item_gallery_handler(
    mutations: MutationsDep, clock: ClockDep, locales: LocalesDep, files: FilesDep
) -> ReplaceCatalogItemGalleryHandler:
    """Собирает отдельный handler сценария replace_catalog_item_gallery."""
    return ReplaceCatalogItemGalleryHandler(
        mutations=mutations, clock=clock, locales=locales, files=files
    )


ReplaceCatalogItemGalleryHandlerDep = Annotated[
    ReplaceCatalogItemGalleryHandler, Depends(get_replace_catalog_item_gallery_handler)
]

from src.modules.catalog.application.catalog_item.command.replace_catalog_item_structure.handler import (
    ReplaceCatalogItemStructureHandler,
)


def get_replace_catalog_item_structure_handler(
    mutations: MutationsDep, clock: ClockDep, structures: StructuresDep, usage: UsageDep
) -> ReplaceCatalogItemStructureHandler:
    """Собирает отдельный handler сценария replace_catalog_item_structure."""
    return ReplaceCatalogItemStructureHandler(
        mutations=mutations, clock=clock, structures=structures, usage=usage
    )


ReplaceCatalogItemStructureHandlerDep = Annotated[
    ReplaceCatalogItemStructureHandler,
    Depends(get_replace_catalog_item_structure_handler),
]

from src.modules.catalog.application.catalog_item.command.set_catalog_item_attributes.handler import (
    SetCatalogItemAttributesHandler,
)


def get_set_catalog_item_attributes_handler(
    mutations: MutationsDep, clock: ClockDep, definitions: DefinitionsDep
) -> SetCatalogItemAttributesHandler:
    """Собирает отдельный handler сценария set_catalog_item_attributes."""
    return SetCatalogItemAttributesHandler(
        mutations=mutations, clock=clock, definitions=definitions
    )


SetCatalogItemAttributesHandlerDep = Annotated[
    SetCatalogItemAttributesHandler, Depends(get_set_catalog_item_attributes_handler)
]

from src.modules.catalog.application.catalog_item.command.set_catalog_item_categories.handler import (
    SetCatalogItemCategoriesHandler,
)


def get_set_catalog_item_categories_handler(
    mutations: MutationsDep, clock: ClockDep, references: ReferencesDep
) -> SetCatalogItemCategoriesHandler:
    """Собирает отдельный handler сценария set_catalog_item_categories."""
    return SetCatalogItemCategoriesHandler(
        mutations=mutations, clock=clock, references=references
    )


SetCatalogItemCategoriesHandlerDep = Annotated[
    SetCatalogItemCategoriesHandler, Depends(get_set_catalog_item_categories_handler)
]

from src.modules.catalog.application.catalog_item.command.set_catalog_item_measurements.handler import (
    SetCatalogItemMeasurementsHandler,
)


def get_set_catalog_item_measurements_handler(
    mutations: MutationsDep, clock: ClockDep
) -> SetCatalogItemMeasurementsHandler:
    """Собирает отдельный handler сценария set_catalog_item_measurements."""
    return SetCatalogItemMeasurementsHandler(mutations=mutations, clock=clock)


SetCatalogItemMeasurementsHandlerDep = Annotated[
    SetCatalogItemMeasurementsHandler,
    Depends(get_set_catalog_item_measurements_handler),
]

from src.modules.catalog.application.catalog_item.command.set_catalog_item_metadata.handler import (
    SetCatalogItemMetadataHandler,
)


def get_set_catalog_item_metadata_handler(
    mutations: MutationsDep, clock: ClockDep
) -> SetCatalogItemMetadataHandler:
    """Собирает отдельный handler сценария set_catalog_item_metadata."""
    return SetCatalogItemMetadataHandler(mutations=mutations, clock=clock)


SetCatalogItemMetadataHandlerDep = Annotated[
    SetCatalogItemMetadataHandler, Depends(get_set_catalog_item_metadata_handler)
]

from src.modules.catalog.application.catalog_item.command.set_catalog_item_price.handler import (
    SetCatalogItemPriceHandler,
)


def get_set_catalog_item_price_handler(
    mutations: MutationsDep, clock: ClockDep, currencies: CurrenciesDep
) -> SetCatalogItemPriceHandler:
    """Собирает отдельный handler сценария set_catalog_item_price."""
    return SetCatalogItemPriceHandler(
        mutations=mutations, clock=clock, currencies=currencies
    )


SetCatalogItemPriceHandlerDep = Annotated[
    SetCatalogItemPriceHandler, Depends(get_set_catalog_item_price_handler)
]

from src.modules.catalog.application.catalog_item.command.set_catalog_item_primary_image.handler import (
    SetCatalogItemPrimaryImageHandler,
)


def get_set_catalog_item_primary_image_handler(
    mutations: MutationsDep, clock: ClockDep, locales: LocalesDep
) -> SetCatalogItemPrimaryImageHandler:
    """Собирает отдельный handler сценария set_catalog_item_primary_image."""
    return SetCatalogItemPrimaryImageHandler(
        mutations=mutations, clock=clock, locales=locales
    )


SetCatalogItemPrimaryImageHandlerDep = Annotated[
    SetCatalogItemPrimaryImageHandler,
    Depends(get_set_catalog_item_primary_image_handler),
]

from src.modules.catalog.application.catalog_item.command.set_catalog_item_sku.handler import (
    SetCatalogItemSkuHandler,
)


def get_set_catalog_item_sku_handler(
    mutations: MutationsDep, clock: ClockDep
) -> SetCatalogItemSkuHandler:
    """Собирает отдельный handler сценария set_catalog_item_sku."""
    return SetCatalogItemSkuHandler(mutations=mutations, clock=clock)


SetCatalogItemSkuHandlerDep = Annotated[
    SetCatalogItemSkuHandler, Depends(get_set_catalog_item_sku_handler)
]

from src.modules.catalog.application.catalog_item.command.set_catalog_item_status.handler import (
    SetCatalogItemStatusHandler,
)


def get_set_catalog_item_status_handler(
    mutations: MutationsDep, clock: ClockDep
) -> SetCatalogItemStatusHandler:
    """Собирает отдельный handler сценария set_catalog_item_status."""
    return SetCatalogItemStatusHandler(mutations=mutations, clock=clock)


SetCatalogItemStatusHandlerDep = Annotated[
    SetCatalogItemStatusHandler, Depends(get_set_catalog_item_status_handler)
]

from src.modules.catalog.application.catalog_item.command.set_catalog_item_stock.handler import (
    SetCatalogItemStockHandler,
)


def get_set_catalog_item_stock_handler(
    mutations: MutationsDep, clock: ClockDep
) -> SetCatalogItemStockHandler:
    """Собирает отдельный handler сценария set_catalog_item_stock."""
    return SetCatalogItemStockHandler(mutations=mutations, clock=clock)


SetCatalogItemStockHandlerDep = Annotated[
    SetCatalogItemStockHandler, Depends(get_set_catalog_item_stock_handler)
]

from src.modules.catalog.application.catalog_item.command.set_catalog_item_tags.handler import (
    SetCatalogItemTagsHandler,
)


def get_set_catalog_item_tags_handler(
    mutations: MutationsDep, clock: ClockDep, references: ReferencesDep
) -> SetCatalogItemTagsHandler:
    """Собирает отдельный handler сценария set_catalog_item_tags."""
    return SetCatalogItemTagsHandler(
        mutations=mutations, clock=clock, references=references
    )


SetCatalogItemTagsHandlerDep = Annotated[
    SetCatalogItemTagsHandler, Depends(get_set_catalog_item_tags_handler)
]

from src.modules.catalog.application.catalog_item.command.set_catalog_item_virtual.handler import (
    SetCatalogItemVirtualHandler,
)


def get_set_catalog_item_virtual_handler(
    mutations: MutationsDep, clock: ClockDep
) -> SetCatalogItemVirtualHandler:
    """Собирает отдельный handler сценария set_catalog_item_virtual."""
    return SetCatalogItemVirtualHandler(mutations=mutations, clock=clock)


SetCatalogItemVirtualHandlerDep = Annotated[
    SetCatalogItemVirtualHandler, Depends(get_set_catalog_item_virtual_handler)
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

from src.modules.catalog.application.catalog_item.query.get_catalog_items_publication_snapshot.handler import (
    GetCatalogItemsPublicationSnapshotHandler,
)


def get_get_catalog_items_publication_snapshot_handler(
    repository: QueriesDep, clock: ClockDep
) -> GetCatalogItemsPublicationSnapshotHandler:
    """Собирает отдельный handler сценария get_catalog_items_publication_snapshot."""
    return GetCatalogItemsPublicationSnapshotHandler(repository=repository, clock=clock)


GetCatalogItemsPublicationSnapshotHandlerDep = Annotated[
    GetCatalogItemsPublicationSnapshotHandler,
    Depends(get_get_catalog_items_publication_snapshot_handler),
]

from src.modules.catalog.application.catalog_item.query.list_catalog_item_variants.handler import (
    ListCatalogItemVariantsHandler,
)


def get_list_catalog_item_variants_handler(
    repository: QueriesDep, clock: ClockDep
) -> ListCatalogItemVariantsHandler:
    """Собирает отдельный handler сценария list_catalog_item_variants."""
    return ListCatalogItemVariantsHandler(repository=repository, clock=clock)


ListCatalogItemVariantsHandlerDep = Annotated[
    ListCatalogItemVariantsHandler, Depends(get_list_catalog_item_variants_handler)
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
