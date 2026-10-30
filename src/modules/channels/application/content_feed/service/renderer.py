from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from uuid import UUID
import logging
from time import perf_counter

from src.modules.channels.application.content_feed.contracts import (
    FeedOverlay,
    FeedSnapshot,
    RenderedFeed,
)
from src.modules.channels.application.content_feed.error import FeedBuildError
from src.modules.channels.application.content_feed.port.access import (
    FeedAccessPort,
    FeedAuthorizationPort,
)
from src.modules.channels.application.content_feed.port.query_repository import (
    ContentFeedQueryRepositoryProtocol,
)
from src.modules.channels.application.content_feed.port.serializer import (
    ContentFeedSerializerProtocol,
)
from src.modules.channels.application.content_feed.port.source import FeedSourcePort
from src.modules.channels.application.content_feed.service.representations import (
    FeedRepresentations,
)
from src.modules.channels.application.content_media.service.galleries import (
    MediaGalleries,
)
from src.modules.channels.domain.content_feed.aggregate import ContentFeed
from src.modules.channels.domain.content_feed.error import ContentFeedError
from src.modules.channels.domain.content_feed.repository import (
    ContentFeedRepositoryProtocol,
)
from src.modules.shared.application.crypto.cipher import Cipher
from src.modules.shared.application.crypto.error import CiphertextUnreadable
from src.modules.shared.application.persistence.unit_of_work import UnitOfWorkProtocol

logger = logging.getLogger(__name__)


class FeedMediaAuthorization:
    """Адаптирует разрешение владельца фида к существующему сервису галерей."""

    def __init__(
        self, *, access: FeedAuthorizationPort, actor_id: UUID, channel_id: UUID
    ) -> None:
        """Закрепляет владельца разрешения для повторных проверок Files."""
        self.access, self.actor_id, self.channel_id = access, actor_id, channel_id

    async def require_files(self, file_ids: tuple[UUID, ...]) -> None:
        """Проверяет действующие права, включая публичный запрос по токену."""
        await self.access.require(
            actor_id=self.actor_id, channel_id=self.channel_id, file_ids=file_ids
        )


class FeedRenderer:
    """Координирует короткие SQL-этапы, получение источника и полный результат."""

    def __init__(
        self,
        *,
        feeds: ContentFeedRepositoryProtocol,
        queries: ContentFeedQueryRepositoryProtocol,
        representations: FeedRepresentations,
        source: FeedSourcePort,
        serializer: ContentFeedSerializerProtocol,
        galleries: MediaGalleries,
        access: FeedAccessPort,
        authorization: FeedAuthorizationPort,
        cipher: Cipher,
        uow: UnitOfWorkProtocol,
        tenant_id: UUID,
    ) -> None:
        """Принимает порты одной внешней сборки без открытия собственного UoW."""
        self.feeds, self.queries, self.representations = feeds, queries, representations
        self.source, self.serializer, self.galleries = source, serializer, galleries
        self.access, self.authorization, self.cipher, self.uow, self.tenant_id = (
            access,
            authorization,
            cipher,
            uow,
            tenant_id,
        )

    async def render(
        self,
        *,
        feed: ContentFeed,
        channel_id: UUID,
        actor_id: UUID,
        public: bool = False,
        token: str = "",
    ) -> RenderedFeed:
        """После изменения контекста допускает одну полную повторную подготовку."""
        started = perf_counter()
        for attempt in range(2):
            try:
                result = await self._render(
                    feed=feed,
                    channel_id=channel_id,
                    actor_id=actor_id,
                    public=public,
                    token=token,
                )
                logger.info(
                    "Content feed rendered",
                    extra={
                        "event": "channels.content_feed.rendered",
                        "tenant_id": str(self.tenant_id),
                        "feed_id": str(feed.id.uuid),
                        "offers": result.statistics.offers,
                        "changed_offers": result.statistics.changed_offers,
                        "duration_ms": round((perf_counter() - started) * 1000, 2),
                    },
                )
                return result
            except FeedBuildError as error:
                if error.code != "feed_context_changed" or attempt:
                    raise
                await self.uow.rollback()
        raise FeedBuildError("feed_context_changed", unavailable=True)

    def require_access(self, feed: ContentFeed, token: str) -> None:
        """Одинаково скрывает выключенный, отозванный и недоступный фид."""
        if (
            not feed.enabled
            or feed.access_token_hash is None
            or not self.access.matches(token, feed.access_token_hash)
        ):
            raise ContentFeedError("feed_not_found")

    async def _render(
        self,
        *,
        feed: ContentFeed,
        channel_id: UUID,
        actor_id: UUID,
        public: bool,
        token: str,
    ) -> RenderedFeed:
        """Завершает SQL до source/storage/сериализации; HTTP получает только готовые байты."""
        if public:
            self.require_access(feed, token)
        await self.authorization.require(
            actor_id=actor_id, channel_id=channel_id, file_ids=()
        )
        try:
            source_url = self.cipher.decrypt(feed.source_url_encrypted).decode("utf-8")
        except (CiphertextUnreadable, UnicodeError):
            raise FeedBuildError("feed_source_unreadable") from None
        settings = self.serializer.validate_settings(feed.source)
        await self.uow.commit()
        source = await self.source.fetch(source_url)
        # Проверка всего исходника выполняется до работы с media и без SQL-транзакции.
        self.serializer.render(source=source, settings=settings, overlays=())
        await self.queries.begin_snapshot()
        await self._current_feed(feed, channel_id, public, token)
        snapshot = await self.representations.snapshot(
            channel_id=channel_id, connection_id=feed.connection_id.uuid
        )
        keys = self._keys(snapshot)
        await self.uow.commit()
        media_access = FeedMediaAuthorization(
            access=self.authorization, actor_id=actor_id, channel_id=channel_id
        )
        galleries = []
        for group in snapshot.groups:
            if any(
                content.gallery
                for target in group.targets
                for content in target.content
            ):
                galleries.extend(
                    await self.galleries.prepare(
                        tenant_id=self.tenant_id,
                        channel_id=channel_id,
                        group_id=group.group_id,
                        expected_revision=group.revision,
                        expected_binding_revision=group.binding_revision,
                        expected_config_revision=group.config_revision,
                        authorization=media_access,
                    )
                )
                await self.uow.commit()
        overlays = []
        for group in snapshot.groups:
            for target in group.targets:
                images = [
                    content.gallery
                    for content in target.content
                    if content.gallery is not None
                ]
                if images and any(
                    tuple(image.file_id for image in value)
                    != tuple(image.file_id for image in images[0])
                    for value in images[1:]
                ):
                    raise FeedBuildError(
                        "feed_gallery_locale_conflict",
                        publication_id=target.publication_id.uuid,
                        field="gallery",
                    )
                prepared = [
                    tuple(image.url for image in gallery.images)
                    for gallery in galleries
                    if gallery.publication_id == target.publication_id.uuid
                ]
                if prepared and any(value != prepared[0] for value in prepared[1:]):
                    raise FeedBuildError(
                        "feed_gallery_locale_conflict",
                        publication_id=target.publication_id.uuid,
                        field="gallery",
                    )
                gallery = prepared[0] if prepared else (() if images else None)
                overlays.append(
                    FeedOverlay(
                        target.publication_id.uuid,
                        keys[target.publication_id.uuid],
                        target,
                        gallery,
                    )
                )
        result = self.serializer.render(
            source=source, settings=settings, overlays=tuple(overlays)
        )
        await self.queries.begin_snapshot()
        await self._current_feed(feed, channel_id, public, token)
        latest = await self.representations.snapshot(
            channel_id=channel_id, connection_id=feed.connection_id.uuid
        )
        if latest != snapshot:
            raise FeedBuildError("feed_context_changed", unavailable=True)
        file_ids = tuple(
            sorted(
                {
                    image.file_id.uuid
                    for group in snapshot.groups
                    for target in group.targets
                    for content in target.content
                    for image in content.gallery or ()
                }
            )
        )
        await self.authorization.require(
            actor_id=actor_id, channel_id=channel_id, file_ids=file_ids
        )
        if file_ids:
            files = {
                file.file_id: file
                for file in await self.galleries.files.describe(file_ids)
            }
            for gallery in galleries:
                for image in gallery.images:
                    media = await self.galleries.queries.get(image.media_id)
                    if (
                        media is None
                        or media.revision != image.revision
                        or media.access_revoked_at is not None
                        or media.file_id not in files
                        or media.source_fingerprint
                        != files[media.file_id].source_fingerprint
                    ):
                        raise FeedBuildError("feed_media_changed", unavailable=True)
        await self.uow.commit()
        return RenderedFeed(result.content, result.statistics, snapshot)

    async def _current_feed(
        self, feed: ContentFeed, channel_id: UUID, public: bool, token: str
    ) -> None:
        """Ротация, выключение или замена источника во время загрузки аннулируют результат."""
        current = await self.feeds.get(
            channel_id=EntityIdVO(channel_id), feed_id=feed.id
        )
        if public:
            self.require_access(current, token)
        if current.revision != feed.revision:
            raise FeedBuildError("feed_context_changed", unavailable=True)

    @staticmethod
    def _keys(snapshot: FeedSnapshot) -> dict[UUID, str]:
        """Не подставляет API ID или SKU при отсутствии подтверждённого import key."""
        owners: dict[str, list[UUID]] = {}
        by_id = {
            value.publication_id: value.import_key for value in snapshot.publications
        }
        for value in snapshot.publications:
            if value.import_key is not None:
                owners.setdefault(value.import_key, []).append(value.publication_id)
        result = {}
        for group in snapshot.groups:
            for target in group.targets:
                identifier = target.publication_id.uuid
                key = by_id.get(identifier)
                if key is None:
                    raise FeedBuildError(
                        "feed_import_key_missing", publication_id=identifier
                    )
                if len(owners[key]) != 1 or identifier in result:
                    raise FeedBuildError(
                        "feed_import_key_duplicate", publication_id=identifier
                    )
                result[identifier] = key
        return result
