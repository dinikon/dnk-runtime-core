from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.application.catalog_import.command.process_catalog_import_row.handler import (
    ProcessCatalogImportRowHandler,
)
from src.modules.catalog.application.catalog_item.creation_service import (
    CatalogItemCreationService,
)
from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.catalog.application.catalog_item.update_service import (
    CatalogItemUpdateService,
)
from src.modules.catalog.infrastructure.catalog_import.repository import (
    SqlAlchemyCatalogImportRepository,
    SqlAlchemyImportRows,
)
from src.modules.catalog.infrastructure.catalog_import.queue import (
    ScheduledCatalogImportQueue,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.repository import (
    SqlAlchemyCatalogItemRepository,
)
from src.modules.catalog.infrastructure.catalog_item.content_schema import (
    SqlAlchemyProductTypeSchemas,
)
from src.modules.catalog.infrastructure.catalog_item.sku import SqlAlchemyCatalogItemSku
from src.modules.catalog.infrastructure.catalog_item.files import FilesCatalogImages
from src.modules.catalog.infrastructure.catalog_import.files import (
    FilesCatalogImportImages,
)
from src.modules.catalog.infrastructure.mutation_lock import PostgresCatalogMutationLock
from src.modules.catalog.infrastructure.locales import ReferenceDataLocales
from src.modules.catalog.infrastructure.currencies import ReferenceDataCurrencies
from src.modules.catalog.infrastructure.rich_text import Nh3RichTextSanitizer
from src.modules.reference_data.infrastructure.persistence.repository import (
    SqlAlchemyCatalogRepository,
)
from src.modules.reference_data.infrastructure.currency.persistence.query_repository import (
    SqlAlchemyCurrencyQueryRepository,
)
from src.modules.reference_data.application.currency.query.validate_currency.handler import (
    ValidateCurrencyHandler,
)
from src.modules.files.infrastructure.assembly import (
    build_files_handlers,
    build_artifact_files_facade,
)
from src.modules.shared.presentation.jobs.management import (
    build_scheduled_job_repository,
)
from src.modules.shared.application.jobs.schedule_scheduled_job_use_case import (
    ScheduleScheduledJobUseCase,
)
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


def build_import_queue(
    session: AsyncSession, tenant_id: UUID
) -> ScheduledCatalogImportQueue:
    """Подключает scheduler к транзакции импорта."""
    return ScheduledCatalogImportQueue(
        tenant_id,
        ScheduleScheduledJobUseCase(
            repository=build_scheduled_job_repository(session),
            clock=UtcClock(),
            uuid_generator=UUID7Generator(),
        ),
        UtcClock(),
    )


def build_process_import_row(
    session: AsyncSession, tenant_id: UUID
) -> ProcessCatalogImportRowHandler:
    """Собирает порты и сервисы Catalog/Files на одной tenant-сессии."""
    clock, uuid = UtcClock(), UUID7Generator()
    items = SqlAlchemyCatalogItemRepository(session)
    mutations = CatalogItemMutationService(items, PostgresCatalogMutationLock(session))
    schemas = SqlAlchemyProductTypeSchemas(session)
    locales = ReferenceDataLocales(SqlAlchemyCatalogRepository(session))
    currencies = ReferenceDataCurrencies(
        ValidateCurrencyHandler(SqlAlchemyCurrencyQueryRepository(session))
    )
    sanitizer = Nh3RichTextSanitizer()
    handlers = build_files_handlers(session)
    files = FilesCatalogImportImages(
        FilesCatalogImages(handlers.upload, handlers.content, handlers.lock_ready),
        handlers.lock_ready,
        build_artifact_files_facade(session),
    )
    creation = CatalogItemCreationService(
        schemas,
        locales,
        currencies,
        SqlAlchemyCatalogItemSku(session),
        sanitizer,
        files,
        clock,
        uuid,
    )
    updates = CatalogItemUpdateService(
        mutations, clock, locales, schemas, sanitizer, currencies, files
    )
    return ProcessCatalogImportRowHandler(
        EntityIdVO(tenant_id),
        SqlAlchemyCatalogImportRepository(session),
        SqlAlchemyImportRows(session),
        items,
        creation,
        mutations,
        updates,
        schemas,
        clock,
    )
