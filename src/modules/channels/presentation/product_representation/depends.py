from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from dataclasses import dataclass
from typing import Annotated
from fastapi import Depends
from src.modules.catalog.application.catalog_item.bindings_facade import (
    CatalogBindingsFacade,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.query_repository import (
    SqlAlchemyCatalogItemQueryRepository,
)
from src.modules.catalog.infrastructure.mutation_lock import PostgresCatalogMutationLock
from src.modules.channels.application.product_representation.service.reader import (
    RepresentationReader,
)
from src.modules.channels.application.product_representation.service.drafts import (
    RepresentationDrafts,
)
from src.modules.channels.application.product_representation.service.writes import (
    RepresentationWrites,
)
from src.modules.channels.application.product_representation.service.builder import (
    RepresentationBuilder,
)
from src.modules.channels.application.product_representation.query.preview_representation.handler import (
    PreviewRepresentationHandler,
)
from src.modules.channels.application.product_representation.query.get_representation.handler import (
    GetRepresentationHandler,
)
from src.modules.channels.infrastructure.catalog_binding.catalog import (
    CatalogBindingGateway,
)
from src.modules.channels.infrastructure.catalog_binding.query_repository import (
    SqlAlchemyCatalogBindingQueryRepository,
)
from src.modules.channels.infrastructure.catalog_binding.repository import (
    SqlAlchemyCatalogBindingRepository,
)
from src.modules.channels.infrastructure.channel.persistence.query_repository import (
    SqlAlchemyChannelQueryRepository,
)
from src.modules.channels.infrastructure.channel.persistence.repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.channels.infrastructure.product_representation.catalog import (
    RepresentationCatalogGateway,
)
from src.modules.channels.infrastructure.product_representation.query_repository import (
    SqlAlchemyRepresentationQueryRepository,
)
from src.modules.channels.infrastructure.product_representation.repository import (
    SqlAlchemyProductRepresentationRepository,
)
from src.modules.channels.infrastructure.product_representation.files import (
    RepresentationFilesGateway,
)
from src.modules.channels.infrastructure.product_representation.rich_text import (
    RepresentationRichTextSanitizer,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.channels.presentation.depends import (
    get_platforms,
    tenant_id_from_context,
)
from src.modules.files.application.stored_file.command.lock_ready_file.handler import (
    LockReadyFileHandler,
)
from src.modules.files.infrastructure.stored_file.persistence.repository import (
    SqlAlchemyStoredFileRepository,
)
from src.modules.files.infrastructure.persistence.query_repository import (
    SqlAlchemyStorageQueryRepository,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.channels.application.product_representation.command.save_representation.handler import (
    SaveRepresentationHandler,
)
from src.modules.channels.application.product_representation.command.enable_representation_export.handler import (
    EnableRepresentationExportHandler,
)
from src.modules.channels.application.product_representation.command.disable_representation_export.handler import (
    DisableRepresentationExportHandler,
)


@dataclass(slots=True)
class RepresentationRuntime:
    """Сервисы одной tenant-сессии, собранные на внешней границе."""

    reader: RepresentationReader
    drafts: RepresentationDrafts
    writes: RepresentationWrites


def build_representation_runtime(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    clock: ClockPort,
    uuid: UUIdGeneratorProtocol,
    platforms: PlatformRegistry,
) -> RepresentationRuntime:
    """Собирает общие сервисы для Console, внешнего media-чтения и Worker."""
    catalog = CatalogBindingsFacade(
        SqlAlchemyCatalogItemQueryRepository(session),
        PostgresCatalogMutationLock(session),
    )
    reader = RepresentationReader(
        channels=SqlAlchemyChannelQueryRepository(session),
        representations=SqlAlchemyRepresentationQueryRepository(session),
        platforms=platforms,
    )
    drafts = RepresentationDrafts(
        builder=RepresentationBuilder(
            catalog=RepresentationCatalogGateway(catalog),
            publications=SqlAlchemyCatalogBindingQueryRepository(session),
        ),
        files=RepresentationFilesGateway(
            tenant_id=tenant_id,
            files=SqlAlchemyStorageQueryRepository(session),
            lock_ready=LockReadyFileHandler(SqlAlchemyStoredFileRepository(session)),
        ),
        rich_text=RepresentationRichTextSanitizer(),
    )
    writes = RepresentationWrites(
        reader=reader,
        drafts=drafts,
        catalog=CatalogBindingGateway(catalog),
        channels=SqlAlchemyChannelRepository(session, tenant_id),
        groups=SqlAlchemyCatalogBindingRepository(session),
        representations=SqlAlchemyProductRepresentationRepository(session),
        uuid=uuid,
        clock=clock,
    )
    return RepresentationRuntime(reader, drafts, writes)


def get_representation_runtime(
    uow: UoWDep,
    clock: ClockDep,
    uuid: UuidDep,
    context: AuthenticatedRequestContextDep,
    platforms: Annotated[InstalledPlatforms, Depends(get_platforms)],
) -> RepresentationRuntime:
    """Подключает Console-контекст к той же внешней сборке общего UoW."""
    return build_representation_runtime(
        session=uow.session,
        tenant_id=tenant_id_from_context(context),
        clock=clock,
        uuid=uuid,
        platforms=platforms,
    )


RepresentationRuntimeDep = Annotated[
    RepresentationRuntime, Depends(get_representation_runtime)
]


def get_preview_representation_handler(
    runtime: RepresentationRuntimeDep, clock: ClockDep
) -> PreviewRepresentationHandler:
    """Собирает конкретный read-сценарий preview."""
    return PreviewRepresentationHandler(
        reader=runtime.reader, drafts=runtime.drafts, clock=clock
    )


PreviewRepresentationHandlerDep = Annotated[
    PreviewRepresentationHandler, Depends(get_preview_representation_handler)
]


def get_representation_handler(
    runtime: RepresentationRuntimeDep,
) -> GetRepresentationHandler:
    """Собирает чтение сохранённых overrides."""
    return GetRepresentationHandler(runtime.reader)


GetRepresentationHandlerDep = Annotated[
    GetRepresentationHandler, Depends(get_representation_handler)
]


def get_save_representation_handler(
    runtime: RepresentationRuntimeDep,
) -> SaveRepresentationHandler:
    """Собирает отдельный сценарий save_representation."""
    return SaveRepresentationHandler(runtime.writes)


SaveRepresentationHandlerDep = Annotated[
    SaveRepresentationHandler, Depends(get_save_representation_handler)
]


def get_enable_representation_export_handler(
    runtime: RepresentationRuntimeDep,
) -> EnableRepresentationExportHandler:
    """Собирает отдельный сценарий enable_representation_export."""
    return EnableRepresentationExportHandler(runtime.writes)


EnableRepresentationExportHandlerDep = Annotated[
    EnableRepresentationExportHandler, Depends(get_enable_representation_export_handler)
]


def get_disable_representation_export_handler(
    runtime: RepresentationRuntimeDep,
) -> DisableRepresentationExportHandler:
    """Собирает отдельный сценарий disable_representation_export."""
    return DisableRepresentationExportHandler(runtime.writes)


DisableRepresentationExportHandlerDep = Annotated[
    DisableRepresentationExportHandler,
    Depends(get_disable_representation_export_handler),
]
