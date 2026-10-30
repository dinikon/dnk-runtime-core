from dataclasses import dataclass
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.application.content_media.service.galleries import (
    MediaGalleries,
)
from src.modules.channels.application.content_media.service.transfers import (
    MediaTransfers,
)
from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.channels.infrastructure.content_media.access_tokens import (
    EncryptedMediaTokens,
)
from src.modules.channels.infrastructure.content_media.files import FilesMediaGateway
from src.modules.channels.infrastructure.content_media.repository import (
    SqlAlchemyContentMediaRepository,
)
from src.modules.channels.infrastructure.content_media.query_repository import (
    SqlAlchemyContentMediaQueryRepository,
)
from src.modules.channels.infrastructure.channel.persistence.repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.channels.presentation.product_representation.depends import (
    build_representation_runtime,
)
from src.modules.files.infrastructure.persistence.query_repository import (
    SqlAlchemyStorageQueryRepository,
)
from src.modules.files.infrastructure.stored_file.persistence.repository import (
    SqlAlchemyStoredFileRepository,
)
from src.modules.files.application.stored_file.command.lock_ready_file.handler import (
    LockReadyFileHandler,
)
from src.modules.files.application.port.storage import StorageResolverProtocol
from src.modules.shared.application.crypto.cipher import Cipher
from src.modules.shared.application.persistence.unit_of_work import UnitOfWorkProtocol
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort


@dataclass(slots=True)
class ContentMediaRuntime:
    """Сборка сервисов media на одной tenant-сессии для HTTP и Worker."""

    galleries: MediaGalleries
    transfers: MediaTransfers


def build_content_media_runtime(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    base_url: str,
    uow: UnitOfWorkProtocol,
    cipher: Cipher,
    clock: ClockPort,
    uuid: UUIdGeneratorProtocol,
    platforms: PlatformRegistry,
    storage: StorageResolverProtocol,
) -> ContentMediaRuntime:
    """Связывает конкретные адаптеры с портами без открытия дополнительного UoW."""
    representation = build_representation_runtime(
        session=session,
        tenant_id=tenant_id,
        clock=clock,
        uuid=uuid,
        platforms=platforms,
    )
    media = SqlAlchemyContentMediaRepository(session)
    tokens = EncryptedMediaTokens(cipher=cipher, base_url=base_url)
    galleries = MediaGalleries(
        reader=representation.reader,
        drafts=representation.drafts,
        writes=representation.writes,
        media=media,
        queries=SqlAlchemyContentMediaQueryRepository(session),
        files=FilesMediaGateway(
            tenant_id=tenant_id,
            queries=SqlAlchemyStorageQueryRepository(session),
            lock=LockReadyFileHandler(SqlAlchemyStoredFileRepository(session)),
            storage=storage,
        ),
        tokens=tokens,
        platforms=platforms,
        uow=uow,
        clock=clock,
        uuid=uuid,
    )
    return ContentMediaRuntime(
        galleries,
        MediaTransfers(
            galleries=galleries,
            channels=SqlAlchemyChannelRepository(session, tenant_id),
            media=media,
            tokens=tokens,
            clock=clock,
        ),
    )
