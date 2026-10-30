from uuid import UUID

from src.modules.channels.application.content_media.port.access import (
    MediaTokenPort,
    MediaAuthorizationPort,
)
from src.modules.channels.application.content_media.service.galleries import (
    MediaGalleries,
)
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.content_media.aggregate import ContentMedia
from src.modules.channels.domain.content_media.error import ContentMediaError
from src.modules.channels.domain.content_media.repository import (
    ContentMediaRepositoryProtocol,
)
from src.modules.channels.domain.content_media.value_object import MediaTransferStatus
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class MediaTransfers:
    """Переходы media на одной сессии; отправка API принадлежит внешнему исполнителю."""

    def __init__(
        self,
        *,
        galleries: MediaGalleries,
        channels: ChannelRepositoryProtocol,
        media: ContentMediaRepositoryProtocol,
        tokens: MediaTokenPort,
        clock: ClockPort,
    ) -> None:
        """Получает write-порты общего UoW, не сетевой клиент."""
        self.galleries, self.channels, self.media, self.tokens, self.clock = (
            galleries,
            channels,
            media,
            tokens,
            clock,
        )

    async def lock(self, *, channel_id: UUID, media_id: UUID) -> ContentMedia:
        """Проверяет владельца до изменения токена или внешнего ID."""
        channel = await self.channels.get(EntityIdVO(channel_id), for_update=True)
        if channel is None:
            raise ContentMediaError("media_not_found")
        media = await self.media.get(EntityIdVO(media_id))
        if media is None or media.connection_id != channel.connection.id:
            raise ContentMediaError("media_not_found")
        return media

    async def revoke(
        self, *, channel_id: UUID, media_id: UUID, expected_revision: int
    ) -> int:
        """Отзывает URL, не удаляя файл и внешний attachment."""
        media = await self.lock(channel_id=channel_id, media_id=media_id)
        media.revoke(expected_revision=expected_revision, now=self.clock.now())
        await self.media.save(media)
        return media.revision

    async def renew(
        self,
        *,
        channel_id: UUID,
        media_id: UUID,
        expected_revision: int,
        authorization: MediaAuthorizationPort,
    ) -> tuple[int, str]:
        """Выдаёт новый секрет только после повторной проверки Files ACL и живой ссылки."""
        row = await self.galleries.queries.get(media_id)
        if row is None or row.channel_id != channel_id:
            raise ContentMediaError("media_not_found")
        await authorization.require_files((row.file_id,))
        if not await self.galleries.is_current_use(row):
            raise ContentMediaError("media_export_not_ready", conflict=True)
        media = await self.lock(channel_id=channel_id, media_id=media_id)
        files = await self.galleries.files.describe((media.file_id.uuid,))
        token_hash, encrypted = self.tokens.issue()
        media.renew_access(
            expected_revision=expected_revision,
            token_hash=token_hash,
            token_encrypted=encrypted,
            now=self.clock.now(),
        )
        await self.media.save(media)
        return media.revision, self.tokens.url(
            media.id.uuid, media.access_token_encrypted, files[0].location.content_type
        )

    async def begin(
        self,
        *,
        tenant_id: UUID,
        channel_id: UUID,
        group_id: UUID,
        expected_revision: int,
        expected_binding_revision: int,
        expected_config_revision: int,
        media_revisions: tuple[tuple[UUID, int], ...],
        operation_id: UUID,
    ) -> tuple[UUID, ...]:
        """Резервирует варианты под тем же барьером, что разрешение и состав группы."""
        context, _ = await self.galleries.writes.lock_context(
            tenant_id=tenant_id, channel_id=channel_id, group_id=group_id
        )
        self.galleries.reader.require_context(
            context,
            expected_revision=expected_revision,
            expected_binding_revision=expected_binding_revision,
            expected_config_revision=expected_config_revision,
        )
        draft = await self.galleries.drafts.prepare(
            context=context, overrides=context.state.overrides, as_of=self.clock.now()
        )
        if not context.state.export_enabled or draft.export_blockers:
            raise ContentMediaError("media_export_not_ready", conflict=True)
        if not media_revisions or len(
            {identifier for identifier, _ in media_revisions}
        ) != len(media_revisions):
            raise ContentMediaError("media_selection_invalid")
        platform = self.galleries.platforms.get(context.channel.platform_kind)
        allowed = {
            (image.file_id.uuid, platform.media_metadata_fingerprint(image.alt))
            for target in draft.prepared.preparation.targets
            for content in target.content
            for image in content.gallery or ()
        }
        pending: list[ContentMedia] = []
        for identifier, revision in sorted(media_revisions):
            media = await self.media.get(EntityIdVO(identifier))
            if (
                media is None
                or media.connection_id.uuid != context.binding.connection_id
                or (media.file_id.uuid, media.metadata_fingerprint) not in allowed
            ):
                raise ContentMediaError("media_not_found")
            media.require_revision(revision)
            if media.transfer_status not in (
                MediaTransferStatus.PENDING,
                MediaTransferStatus.FAILED,
                MediaTransferStatus.READY,
            ):
                raise ContentMediaError("media_transfer_unresolved", conflict=True)
            pending.append(media)
        await self.galleries.files.describe(
            tuple(media.file_id.uuid for media in pending), for_update=True
        )
        started: list[UUID] = []
        for media in pending:
            if media.begin_transfer(
                expected_revision=media.revision,
                operation_id=EntityIdVO(operation_id),
                now=self.clock.now(),
            ):
                await self.media.save(media)
                started.append(media.id.uuid)
        return tuple(started)

    async def record(
        self,
        *,
        channel_id: UUID,
        config_revision: int,
        identity_namespace: str,
        identity_key: str,
        operation_id: UUID,
        media_id: UUID,
        expected_revision: int,
        remote_id: str | None,
        error: str | None,
        uncertain: bool,
    ) -> bool:
        """Фиксирует подтверждённый ID или unknown; устаревший контекст не разрешает повтор."""
        channel = await self.channels.get(EntityIdVO(channel_id), for_update=True)
        if channel is None:
            return False
        media = await self.media.get(EntityIdVO(media_id))
        if media is None or media.connection_id != channel.connection.id:
            return False
        identity = channel.connection.identity
        if (
            channel.connection.config_revision != config_revision
            or identity is None
            or (identity.namespace, identity.key) != (identity_namespace, identity_key)
        ):
            remote_id, error, uncertain = None, "media_context_changed", True
        applied = media.record_result(
            expected_revision=expected_revision,
            operation_id=EntityIdVO(operation_id),
            remote_id=remote_id,
            error=error,
            uncertain=uncertain,
            now=self.clock.now(),
        )
        if applied:
            await self.media.save(media)
        return applied
