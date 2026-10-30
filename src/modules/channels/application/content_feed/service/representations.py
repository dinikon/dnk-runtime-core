from uuid import UUID
from src.modules.channels.application.port.platform import PlatformRegistry

from src.modules.channels.application.channel.port.query_repository import (
    ChannelQueryRepository,
)
from src.modules.channels.application.content_feed.contracts import (
    FeedGroupSnapshot,
    FeedSnapshot,
)
from src.modules.channels.application.content_feed.error import FeedBuildError
from src.modules.channels.application.content_feed.port.query_repository import (
    ContentFeedQueryRepositoryProtocol,
)
from src.modules.channels.application.product_representation.service.reader import (
    RepresentationReader,
)
from src.modules.channels.application.product_representation.service.drafts import (
    RepresentationDrafts,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class FeedRepresentations:
    """Собирает существующие представления в рамках одного согласованного read-этапа."""

    def __init__(
        self,
        *,
        queries: ContentFeedQueryRepositoryProtocol,
        channels: ChannelQueryRepository,
        platforms: PlatformRegistry,
        reader: RepresentationReader,
        drafts: RepresentationDrafts,
        clock: ClockPort,
    ) -> None:
        """Получает публичные порты и общий путь подготовки, без SQLAlchemy."""
        self.queries, self.channels, self.reader, self.drafts, self.clock = (
            queries,
            channels,
            reader,
            drafts,
            clock,
        )
        self.platforms = platforms

    async def snapshot(self, *, channel_id: UUID, connection_id: UUID) -> FeedSnapshot:
        """Не пропускает ошибочные разрешённые группы ради частично успешного XML."""
        channel = await self.channels.get(channel_id)
        if channel is None:
            raise FeedBuildError("feed_channel_not_found")
        if (
            "content_feed"
            not in self.platforms.get(
                channel.platform_kind
            ).manifest.supported_capabilities
        ):
            raise FeedBuildError("feed_platform_unsupported")
        if (
            channel.identity is None
            or channel.verification.status != "verified"
            or channel.verification.config_revision != channel.config_revision
            or channel.recovery_required
        ):
            raise FeedBuildError("feed_connection_unverified")
        if await self.queries.connection_id(channel_id) != connection_id:
            raise FeedBuildError("feed_context_changed", unavailable=True)
        groups = []
        for group_id in await self.queries.groups(connection_id):
            context = await self.reader.load(channel_id=channel_id, group_id=group_id)
            draft = await self.drafts.prepare(
                context=context,
                overrides=context.state.overrides,
                as_of=self.clock.now(),
            )
            if not context.state.export_enabled or draft.export_blockers:
                raise FeedBuildError("feed_representation_not_ready")
            groups.append(
                FeedGroupSnapshot(
                    group_id,
                    context.state.revision,
                    context.binding.revision,
                    context.channel.config_revision,
                    draft.prepared.preparation.targets,
                )
            )
        return FeedSnapshot(
            connection_id,
            channel.revision,
            tuple(groups),
            await self.queries.publications(connection_id),
        )
