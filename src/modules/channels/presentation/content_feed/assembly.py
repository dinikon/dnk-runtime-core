from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.channels.application.content_feed.service.management import (
    ContentFeedManagement,
)
from src.modules.channels.application.content_feed.service.renderer import FeedRenderer
from src.modules.channels.application.content_feed.service.representations import (
    FeedRepresentations,
)
from src.modules.channels.application.content_feed.port.source import FeedSourcePort
from src.modules.channels.infrastructure.content_feed.source import HttpsFeedSource
from src.modules.channels.infrastructure.content_feed.access_tokens import (
    EncryptedFeedTokens,
)
from src.modules.channels.infrastructure.content_feed.authorization import (
    FeedAuthorization,
)
from src.modules.channels.infrastructure.content_feed.persistence.repository import (
    SqlAlchemyContentFeedRepository,
)
from src.modules.channels.infrastructure.content_feed.persistence.query_repository import (
    SqlAlchemyContentFeedQueryRepository,
)
from src.modules.channels.infrastructure.channel.persistence.query_repository import (
    SqlAlchemyChannelQueryRepository,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.channels.presentation.content_media.assembly import (
    build_content_media_runtime,
)
from src.modules.files.application.port.storage import StorageResolverProtocol
from src.modules.identity.application.access.authorization_service_protocol import (
    AuthorizationServiceProtocol,
)
from src.modules.shared.application.crypto.cipher import Cipher
from src.modules.shared.application.persistence.unit_of_work import UnitOfWorkProtocol
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.channels.application.content_feed.service.imports import FeedImports
from src.modules.channels.infrastructure.content_feed.jobs import SharedFeedImportJobs
from src.modules.channels.infrastructure.channel.persistence.repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.shared.presentation.jobs.management import (
    build_scheduled_job_repository,
)


@dataclass(slots=True)
class ContentFeedRuntime:
    """Сборка сценариев фида на одной tenant-сессии."""

    management: ContentFeedManagement
    imports: FeedImports


def build_content_feed_runtime(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    base_url: str,
    uow: UnitOfWorkProtocol,
    cipher: Cipher,
    clock: ClockPort,
    uuid: UUIdGeneratorProtocol,
    platforms: InstalledPlatforms,
    storage: StorageResolverProtocol,
    authorization: AuthorizationServiceProtocol,
    source: FeedSourcePort | None = None,
) -> ContentFeedRuntime:
    """Переиспользует representation/media и связывает порты без дополнительных UoW."""
    media = build_content_media_runtime(
        session=session,
        tenant_id=tenant_id,
        base_url=base_url,
        uow=uow,
        cipher=cipher,
        clock=clock,
        uuid=uuid,
        platforms=platforms,
        storage=storage,
    )
    feeds = SqlAlchemyContentFeedRepository(session)
    queries = SqlAlchemyContentFeedQueryRepository(session)
    channels = SqlAlchemyChannelQueryRepository(session)
    serializer = platforms.content_feed_serializer("prom")
    tokens = EncryptedFeedTokens(cipher=cipher, base_url=base_url)
    source = source if source is not None else HttpsFeedSource()
    representations = FeedRepresentations(
        queries=queries,
        channels=channels,
        platforms=platforms,
        reader=media.galleries.reader,
        drafts=media.galleries.drafts,
        clock=clock,
    )
    renderer = FeedRenderer(
        feeds=feeds,
        queries=queries,
        representations=representations,
        source=source,
        serializer=serializer,
        galleries=media.galleries,
        access=tokens,
        authorization=FeedAuthorization(
            tenant_id=tenant_id, authorization=authorization
        ),
        cipher=cipher,
        uow=uow,
        tenant_id=tenant_id,
    )
    return ContentFeedRuntime(
        ContentFeedManagement(
            feeds=feeds,
            queries=queries,
            channels=channels,
            platforms=platforms,
            source=source,
            serializer=serializer,
            access=tokens,
            renderer=renderer,
            cipher=cipher,
            clock=clock,
            uuid=uuid,
        ),
        FeedImports(
            feeds=feeds,
            queries=queries,
            channels=SqlAlchemyChannelRepository(session, tenant_id),
            platforms=platforms,
            renderer=renderer,
            importer=platforms.feed_importer("prom"),
            access=tokens,
            authorization=FeedAuthorization(
                tenant_id=tenant_id, authorization=authorization
            ),
            jobs=SharedFeedImportJobs(build_scheduled_job_repository(session)),
            cipher=cipher,
            uow=uow,
            clock=clock,
            uuid=uuid,
            tenant_id=tenant_id,
        ),
    )
