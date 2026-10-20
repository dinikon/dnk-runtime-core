from src.modules.catalog.infrastructure.rich_text import Nh3RichTextSanitizer
from src.modules.catalog.infrastructure.catalog_item.files import FilesCatalogImages
from src.modules.files.infrastructure.assembly import build_files_handlers
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.catalog.application.catalog_item.facade import (
    CatalogItemsFacadeProtocol,
)
from src.modules.catalog.application.catalog_item.creation_service import (
    CatalogItemCreationService,
)
from src.modules.catalog.application.catalog_item.command.create_catalog_item.handler import (
    CreateCatalogItemHandler,
)
from src.modules.catalog.application.catalog_item.query.validate_catalog_draft.handler import (
    ValidateCatalogDraftHandler,
)
from src.modules.catalog.application.catalog_item.command.lock_catalog_item_for_binding.handler import (
    LockCatalogItemForBindingHandler,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_items.handler import (
    ListCatalogItemsHandler,
)
from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.repository import (
    SqlAlchemyCatalogItemRepository,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.query_repository import (
    SqlAlchemyCatalogItemQueryRepository,
)
from src.modules.catalog.infrastructure.catalog_item.content_schema import (
    SqlAlchemyProductTypeSchemas,
)
from src.modules.catalog.infrastructure.catalog_item.sku import SqlAlchemyCatalogItemSku
from src.modules.catalog.infrastructure.catalog_item.facade import CatalogItemsFacade
from src.modules.catalog.application.catalog_item.query.get_catalog_items_publication_snapshot.handler import (
    GetCatalogItemsPublicationSnapshotHandler,
)
from src.modules.catalog.infrastructure.mutation_lock import PostgresCatalogMutationLock
from src.modules.catalog.infrastructure.locales import ReferenceDataLocales
from src.modules.catalog.infrastructure.currencies import ReferenceDataCurrencies
from src.modules.reference_data.infrastructure.persistence.repository import (
    SqlAlchemyCatalogRepository,
)
from src.modules.reference_data.infrastructure.currency.persistence.query_repository import (
    SqlAlchemyCurrencyQueryRepository,
)
from src.modules.reference_data.application.currency.query.validate_currency.handler import (
    ValidateCurrencyHandler,
)


def build_catalog_items_facade(
    session: AsyncSession, clock: ClockPort, uuid: UUIdGeneratorProtocol
) -> CatalogItemsFacadeProtocol:
    """Собирает публичный фасад на уже открытом UoW без транзакционной границы."""
    files = build_files_handlers(session)
    repository = SqlAlchemyCatalogItemRepository(session)
    drafts = CatalogItemCreationService(
        SqlAlchemyProductTypeSchemas(session),
        ReferenceDataLocales(SqlAlchemyCatalogRepository(session)),
        ReferenceDataCurrencies(
            ValidateCurrencyHandler(SqlAlchemyCurrencyQueryRepository(session))
        ),
        SqlAlchemyCatalogItemSku(session),
        Nh3RichTextSanitizer(),
        FilesCatalogImages(files.upload, files.content, files.lock_ready),
        clock,
        uuid,
    )
    return CatalogItemsFacade(
        CreateCatalogItemHandler(repository, drafts),
        ValidateCatalogDraftHandler(drafts),
        ListCatalogItemsHandler(SqlAlchemyCatalogItemQueryRepository(session), clock),
        LockCatalogItemForBindingHandler(
            CatalogItemMutationService(repository, PostgresCatalogMutationLock(session))
        ),
        GetCatalogItemsPublicationSnapshotHandler(
            SqlAlchemyCatalogItemQueryRepository(session), clock
        ),
    )
