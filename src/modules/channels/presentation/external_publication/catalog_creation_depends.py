from typing import Annotated
from fastapi import Depends
from src.config import dnk_config
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.shared.presentation.crypto.depends import get_cipher
from src.modules.shared.infrastructure.persistence.database_helper import db_helper
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.channels.presentation.depends import (
    get_platforms,
    tenant_id_from_context,
)
from src.modules.channels.application.external_publication.command.create_catalog_from_publication.handler import (
    CreateCatalogFromPublicationHandler,
)
from src.modules.channels.application.external_publication.port.catalog_creation import (
    PublicationImagesPort,
)
from src.modules.channels.infrastructure.external_publication.catalog_creation.query_repository import (
    SqlAlchemyPublicationCreationRead,
)
from src.modules.channels.infrastructure.external_publication.catalog_creation.catalog import (
    CatalogPublicationGateway,
)
from src.modules.channels.infrastructure.channel.persistence.repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.channels.infrastructure.catalog_binding.repository import (
    SqlAlchemyCatalogBindingRepository,
)
from src.modules.channels.infrastructure.catalog_binding.query_repository import (
    SqlAlchemyCatalogBindingQueryRepository,
)
from src.modules.channels.infrastructure.catalog_binding.catalog import (
    CatalogBindingGateway,
)
from src.modules.channels.application.catalog_binding.views import BindingViews
from src.modules.channels.application.catalog_binding.writes import BindingWrites
from src.modules.catalog.application.catalog_item.bindings_facade import (
    CatalogBindingsFacade,
)
from src.modules.catalog.application.catalog_item.publication_creation import (
    PublicationCatalogCreation,
)
from src.modules.catalog.application.catalog_item.creation_service import (
    CatalogItemCreationService,
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
from src.modules.catalog.infrastructure.catalog_item.files import FilesCatalogImages
from src.modules.catalog.infrastructure.catalog_import.files import (
    FilesCatalogImportImages,
)
from src.modules.catalog.infrastructure.catalog_item.publication_media import (
    PublicationImageDownloader,
)
from src.modules.catalog.presentation.catalog_import.runtime import CatalogImportRuntime
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


def get_publication_images(
    context: AuthenticatedRequestContextDep,
) -> PublicationImagesPort:
    """Собирает независимые короткие Files фазы, не используя request session для сети."""
    return PublicationImageDownloader(
        CatalogImportRuntime(db_helper.session_factory, tenant_id_from_context(context))
    )


PublicationImagesDep = Annotated[PublicationImagesPort, Depends(get_publication_images)]


def get_create_catalog_from_publication_handler(
    uow: UoWDep,
    context: AuthenticatedRequestContextDep,
    images: PublicationImagesDep,
    clock: ClockDep,
    uuid: UuidDep,
) -> CreateCatalogFromPublicationHandler:
    """Подключает Catalog и Channels к одному UoW для атомарного сохранения."""
    session = uow.session
    lock = PostgresCatalogMutationLock(session)
    skus = SqlAlchemyCatalogItemSku(session)
    files = build_files_handlers(session)
    creation = CatalogItemCreationService(
        SqlAlchemyProductTypeSchemas(session),
        ReferenceDataLocales(SqlAlchemyCatalogRepository(session)),
        ReferenceDataCurrencies(
            ValidateCurrencyHandler(SqlAlchemyCurrencyQueryRepository(session))
        ),
        skus,
        Nh3RichTextSanitizer(),
        FilesCatalogImportImages(
            FilesCatalogImages(files.upload, files.content, files.lock_ready),
            files.lock_ready,
            build_artifact_files_facade(session),
        ),
        clock,
        uuid,
    )
    catalog = CatalogBindingGateway(
        CatalogBindingsFacade(SqlAlchemyCatalogItemQueryRepository(session), lock)
    )
    read = SqlAlchemyCatalogBindingQueryRepository(session)
    channels = SqlAlchemyChannelRepository(session, tenant_id_from_context(context))
    views = BindingViews(catalog, read)
    return CreateCatalogFromPublicationHandler(
        read=SqlAlchemyPublicationCreationRead(session),
        channels=channels,
        platforms=get_platforms(),
        cipher=get_cipher(),
        catalog=CatalogPublicationGateway(
            PublicationCatalogCreation(
                creation=creation,
                repository=SqlAlchemyCatalogItemRepository(session),
                skus=skus,
                lock=lock,
            )
        ),
        images=images,
        bindings=read,
        views=views,
        writes=BindingWrites(
            catalog, SqlAlchemyCatalogBindingRepository(session), channels, views, uuid
        ),
        uow=uow,
        uuid=uuid,
        clock=clock,
        max_images=dnk_config.CATALOG_IMPORT.max_images,
    )


CreateCatalogFromPublicationHandlerDep = Annotated[
    CreateCatalogFromPublicationHandler,
    Depends(get_create_catalog_from_publication_handler),
]
