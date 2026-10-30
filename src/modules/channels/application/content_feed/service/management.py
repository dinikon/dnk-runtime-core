from uuid import UUID
from src.modules.channels.application.port.platform import PlatformRegistry

from src.modules.channels.application.channel.port.query_repository import (
    ChannelQueryRepository,
)
from src.modules.channels.application.content_feed.contracts import (
    FeedDetails,
    FeedReadRow,
    RenderedFeed,
)
from src.modules.channels.application.content_feed.error import FeedBuildError
from src.modules.channels.application.content_feed.port.access import FeedAccessPort
from src.modules.channels.application.content_feed.port.query_repository import (
    ContentFeedQueryRepositoryProtocol,
)
from src.modules.channels.application.content_feed.port.serializer import (
    ContentFeedSerializerProtocol,
)
from src.modules.channels.application.content_feed.port.source import FeedSourcePort
from src.modules.channels.application.content_feed.service.renderer import FeedRenderer
from src.modules.channels.domain.content_feed.aggregate import ContentFeed
from src.modules.channels.domain.content_feed.error import ContentFeedError
from src.modules.channels.domain.content_feed.repository import (
    ContentFeedRepositoryProtocol,
)
from src.modules.channels.domain.content_feed.value_object import FeedSourceVO
from src.modules.shared.application.crypto.cipher import Cipher
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ContentFeedManagement:
    """Общие операции отдельных команд; транзакцией управляет внешняя сборка."""

    def __init__(
        self,
        *,
        feeds: ContentFeedRepositoryProtocol,
        queries: ContentFeedQueryRepositoryProtocol,
        channels: ChannelQueryRepository,
        platforms: PlatformRegistry,
        source: FeedSourcePort,
        serializer: ContentFeedSerializerProtocol,
        access: FeedAccessPort,
        renderer: FeedRenderer,
        cipher: Cipher,
        clock: ClockPort,
        uuid: UUIdGeneratorProtocol,
    ) -> None:
        """Получает конкретные порты и общий путь полной проверки."""
        self.feeds, self.queries, self.channels = feeds, queries, channels
        self.platforms = platforms
        self.source, self.serializer, self.access, self.renderer = (
            source,
            serializer,
            access,
            renderer,
        )
        self.cipher, self.clock, self.uuid = cipher, clock, uuid

    def details(self, row: FeedReadRow) -> FeedDetails:
        """Возвращает только публичные поля; создание возможно до настройки origin."""
        url = None
        if row.token_encrypted is not None:
            try:
                url = self.access.url(row.id, row.token_encrypted)
            except FeedBuildError as error:
                if error.code != "feed_public_origin_unavailable":
                    raise
        return FeedDetails(
            row.id,
            row.revision,
            row.enabled,
            row.scope_key,
            row.source_schema,
            row.source_settings,
            url,
            row.created_at,
            row.updated_at,
        )

    async def get(self, *, channel_id: UUID, feed_id: UUID) -> FeedDetails:
        """Читает проекцию без Domain restore."""
        return self.details(
            await self.queries.details(channel_id=channel_id, feed_id=feed_id)
        )

    async def list(self, channel_id: UUID) -> tuple[FeedDetails, ...]:
        """Читает все настройки одним SQL-запросом."""
        return tuple(self.details(row) for row in await self.queries.list(channel_id))

    async def create(
        self, *, channel_id: UUID, source_url: str, source: FeedSourceVO, actor_id: UUID
    ) -> FeedDetails:
        """Создаёт только конфигурацию, не загружает источник и не включает выдачу."""
        channel = await self.channels.get(channel_id)
        if channel is None:
            raise ContentFeedError("feed_channel_not_found")
        if (
            "content_feed"
            not in self.platforms.get(
                channel.platform_kind
            ).manifest.supported_capabilities
        ):
            raise FeedBuildError("feed_platform_unsupported")
        settings = self.serializer.validate_settings(source)
        url = self.source.validate_url(source_url)
        token_hash, encrypted = self.access.issue()
        feed = ContentFeed.create(
            identifier=EntityIdVO(self.uuid.new()),
            connection_id=EntityIdVO(await self.queries.connection_id(channel_id)),
            source=settings,
            source_url_encrypted=self.cipher.encrypt(url.encode()),
            token_hash=token_hash,
            token_encrypted=encrypted,
            actor=EntityIdVO(actor_id),
            now=self.clock.now(),
        )
        await self.feeds.add(feed)
        return await self.get(channel_id=channel_id, feed_id=feed.id.uuid)

    async def change_source(
        self,
        *,
        channel_id: UUID,
        feed_id: UUID,
        source_url: str | None,
        source: FeedSourceVO,
        expected_revision: int,
        actor_id: UUID,
    ) -> FeedDetails:
        """Не меняет ciphertext и ревизию при сохранении того же URL и настроек."""
        feed = await self.feeds.get(
            channel_id=EntityIdVO(channel_id), feed_id=EntityIdVO(feed_id)
        )
        feed.require_revision(expected_revision)
        settings = self.serializer.validate_settings(source)
        encrypted = feed.source_url_encrypted
        if source_url is not None:
            url = self.source.validate_url(source_url)
            if self.cipher.decrypt(encrypted).decode() != url:
                encrypted = self.cipher.encrypt(url.encode())
        feed.change_source(
            source=settings,
            encrypted_url=encrypted,
            expected_revision=expected_revision,
            actor=EntityIdVO(actor_id),
            now=self.clock.now(),
        )
        await self.feeds.save(feed, expected_revision=expected_revision)
        return await self.get(channel_id=channel_id, feed_id=feed_id)

    async def enable(
        self, *, channel_id: UUID, feed_id: UUID, expected_revision: int, actor_id: UUID
    ) -> FeedDetails:
        """Проверяет полный фид до CAS-включения; никакого импорта Prom не запускает."""
        feed = await self.feeds.get(
            channel_id=EntityIdVO(channel_id), feed_id=EntityIdVO(feed_id)
        )
        feed.require_revision(expected_revision)
        if feed.access_token_encrypted is None:
            raise ContentFeedError("feed_access_revoked")
        self.access.url(feed.id.uuid, feed.access_token_encrypted)
        await self.renderer.render(feed=feed, channel_id=channel_id, actor_id=actor_id)
        feed.enable(
            expected_revision=expected_revision,
            blockers=(),
            actor=EntityIdVO(actor_id),
            now=self.clock.now(),
        )
        await self.feeds.save(feed, expected_revision=expected_revision)
        return await self.get(channel_id=channel_id, feed_id=feed_id)

    async def disable(
        self, *, channel_id: UUID, feed_id: UUID, expected_revision: int, actor_id: UUID
    ) -> FeedDetails:
        """Запрещает выдачу без обращения к исходному серверу."""
        feed = await self.feeds.get(
            channel_id=EntityIdVO(channel_id), feed_id=EntityIdVO(feed_id)
        )
        feed.disable(
            expected_revision=expected_revision,
            actor=EntityIdVO(actor_id),
            now=self.clock.now(),
        )
        await self.feeds.save(feed, expected_revision=expected_revision)
        return await self.get(channel_id=channel_id, feed_id=feed_id)

    async def rotate_access(
        self, *, channel_id: UUID, feed_id: UUID, expected_revision: int, actor_id: UUID
    ) -> FeedDetails:
        """Заменяет токен с CAS, делая прежнюю ссылку недействительной."""
        feed = await self.feeds.get(
            channel_id=EntityIdVO(channel_id), feed_id=EntityIdVO(feed_id)
        )
        feed.require_revision(expected_revision)
        token_hash, encrypted = self.access.issue()
        feed.rotate_access_token(
            token_hash=token_hash,
            token_encrypted=encrypted,
            expected_revision=expected_revision,
            actor=EntityIdVO(actor_id),
            now=self.clock.now(),
        )
        await self.feeds.save(feed, expected_revision=expected_revision)
        return await self.get(channel_id=channel_id, feed_id=feed_id)

    async def revoke_access(
        self, *, channel_id: UUID, feed_id: UUID, expected_revision: int, actor_id: UUID
    ) -> FeedDetails:
        """Отзывает доступ без выпуска замещающего токена."""
        feed = await self.feeds.get(
            channel_id=EntityIdVO(channel_id), feed_id=EntityIdVO(feed_id)
        )
        feed.revoke_access(
            expected_revision=expected_revision,
            actor=EntityIdVO(actor_id),
            now=self.clock.now(),
        )
        await self.feeds.save(feed, expected_revision=expected_revision)
        return await self.get(channel_id=channel_id, feed_id=feed_id)

    async def delete(
        self, *, channel_id: UUID, feed_id: UUID, expected_revision: int
    ) -> None:
        """Удаляет фид с проверкой ревизии, не меняя представления или источник."""
        feed = await self.feeds.get(
            channel_id=EntityIdVO(channel_id), feed_id=EntityIdVO(feed_id)
        )
        feed.require_revision(expected_revision)
        await self.feeds.delete(feed, expected_revision=expected_revision)

    async def preview(
        self, *, channel_id: UUID, feed_id: UUID, actor_id: UUID
    ) -> RenderedFeed:
        """Использует тот же путь сборки для сохранённого, в том числе выключенного фида."""
        feed = await self.feeds.get(
            channel_id=EntityIdVO(channel_id), feed_id=EntityIdVO(feed_id)
        )
        return await self.renderer.render(
            feed=feed, channel_id=channel_id, actor_id=actor_id
        )

    async def public(self, *, feed_id: UUID, token: str) -> RenderedFeed:
        """Не принимает actor или tenant из публичного запроса."""
        channel_id = await self.queries.channel_for_feed(feed_id)
        feed = await self.feeds.get(
            channel_id=EntityIdVO(channel_id), feed_id=EntityIdVO(feed_id)
        )
        return await self.renderer.render(
            feed=feed,
            channel_id=channel_id,
            actor_id=feed.updated_by.uuid,
            public=True,
            token=token,
        )
