from uuid import UUID

from src.modules.channels.application.content_media.contracts import (
    PreparedGallery,
    PreparedGalleryImage,
    MediaReadRow,
)
from src.modules.channels.application.content_media.port.access import (
    MediaAuthorizationPort,
    MediaTokenPort,
)
from src.modules.channels.application.content_media.port.files import MediaFilesPort
from src.modules.channels.application.content_media.port.query_repository import (
    ContentMediaQueryRepositoryProtocol,
)
from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.channels.application.product_representation.service.reader import (
    RepresentationReader,
)
from src.modules.channels.application.product_representation.service.drafts import (
    RepresentationDrafts,
)
from src.modules.channels.application.product_representation.service.writes import (
    RepresentationWrites,
)
from src.modules.channels.domain.content_media.aggregate import ContentMedia
from src.modules.channels.domain.content_media.error import ContentMediaError
from src.modules.channels.domain.content_media.repository import (
    ContentMediaRepositoryProtocol,
)
from src.modules.shared.application.persistence.unit_of_work import UnitOfWorkProtocol
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class MediaGalleries:
    """Координирует двухфазную подготовку и актуальность использования изображения."""

    def __init__(
        self,
        *,
        reader: RepresentationReader,
        drafts: RepresentationDrafts,
        writes: RepresentationWrites,
        media: ContentMediaRepositoryProtocol,
        queries: ContentMediaQueryRepositoryProtocol,
        files: MediaFilesPort,
        tokens: MediaTokenPort,
        platforms: PlatformRegistry,
        uow: UnitOfWorkProtocol,
        clock: ClockPort,
        uuid: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает сервисы одной внешней сессии и порты сетевых операций."""
        self.reader, self.drafts, self.writes = reader, drafts, writes
        self.media, self.queries, self.files = media, queries, files
        self.tokens, self.platforms, self.uow, self.clock, self.uuid = (
            tokens,
            platforms,
            uow,
            clock,
            uuid,
        )

    async def prepare(
        self,
        *,
        tenant_id: UUID,
        channel_id: UUID,
        group_id: UUID,
        expected_revision: int,
        expected_binding_revision: int,
        expected_config_revision: int,
        authorization: MediaAuthorizationPort,
    ) -> tuple[PreparedGallery, ...]:
        """Проверяет storage вне транзакции, затем перечитывает контекст под locks."""
        context = await self.reader.load(channel_id=channel_id, group_id=group_id)
        self.reader.require_context(
            context,
            expected_revision=expected_revision,
            expected_binding_revision=expected_binding_revision,
            expected_config_revision=expected_config_revision,
        )
        draft = await self.drafts.prepare(
            context=context, overrides=context.state.overrides, as_of=self.clock.now()
        )
        if not context.state.export_enabled or draft.export_blockers:
            raise ContentMediaError("media_export_not_ready", conflict=True)
        file_ids = tuple(
            sorted(
                {
                    image.file_id.uuid
                    for target in draft.prepared.preparation.targets
                    for content in target.content
                    for image in content.gallery or ()
                }
            )
        )
        await authorization.require_files(file_ids)
        files = await self.files.describe(file_ids)
        supported = self.platforms.get(
            context.channel.platform_kind
        ).manifest.media_supported_types
        if supported and any(
            file.location.content_type not in supported for file in files
        ):
            raise ContentMediaError("media_format_unsupported")
        await self.uow.commit()
        await self.files.inspect(files)
        current, _ = await self.writes.lock_context(
            tenant_id=tenant_id, channel_id=channel_id, group_id=group_id
        )
        self.reader.require_context(
            current,
            expected_revision=expected_revision,
            expected_binding_revision=expected_binding_revision,
            expected_config_revision=expected_config_revision,
        )
        latest = await self.drafts.prepare(
            context=current, overrides=current.state.overrides, as_of=self.clock.now()
        )
        if (
            not current.state.export_enabled
            or latest.export_blockers
            or latest.prepared.preparation != draft.prepared.preparation
        ):
            raise ContentMediaError("media_context_changed", conflict=True)
        locked_files = await self.files.describe(file_ids, for_update=True)
        if files != locked_files:
            raise ContentMediaError("media_context_changed", conflict=True)
        await authorization.require_files(file_ids)
        by_file = {file.file_id: file for file in files}
        platform = self.platforms.get(current.channel.platform_kind)
        prepared: list[PreparedGallery] = []
        targets = latest.prepared.preparation.targets
        for target in targets:
            parent = next(
                (
                    value.external_id
                    for value in targets
                    if value.publication_id == target.parent_publication_id
                ),
                None,
            )
            for content in target.content:
                if content.gallery is None:
                    continue
                images: list[PreparedGalleryImage] = []
                for image in content.gallery:
                    file = by_file[image.file_id.uuid]
                    fingerprint = platform.media_metadata_fingerprint(image.alt)
                    media = await self.media.find(
                        connection_id=EntityIdVO(current.binding.connection_id),
                        file_id=image.file_id,
                        source_fingerprint=file.source_fingerprint,
                        metadata_fingerprint=fingerprint,
                    )
                    if media is None:
                        token_hash, encrypted = self.tokens.issue()
                        media = ContentMedia.create(
                            identifier=EntityIdVO(self.uuid.new()),
                            connection_id=EntityIdVO(current.binding.connection_id),
                            file_id=image.file_id,
                            source_fingerprint=file.source_fingerprint,
                            metadata_fingerprint=fingerprint,
                            token_hash=token_hash,
                            token_encrypted=encrypted,
                            requires_transfer=platform.manifest.media_remote_ids,
                            now=self.clock.now(),
                        )
                        await self.media.save(media)
                    if media.access_revoked_at is not None:
                        raise ContentMediaError("media_access_revoked", conflict=True)
                    images.append(
                        PreparedGalleryImage(
                            media.id.uuid,
                            media.revision,
                            file.file_id,
                            image.alt,
                            image.caption,
                            media.remote_media_id,
                            media.transfer_status,
                            self.tokens.url(
                                media.id.uuid,
                                media.access_token_encrypted,
                                file.location.content_type,
                            ),
                        )
                    )
                prepared.append(
                    PreparedGallery(
                        target.publication_id.uuid,
                        target.external_id or "",
                        parent,
                        target.publication_kind or "",
                        content.locale,
                        tuple(images),
                    )
                )
        return tuple(prepared)

    async def is_current_use(self, media: MediaReadRow) -> bool:
        """Не даёт старому кешу разрешать чтение файла, исчезнувшего из итоговых галерей."""
        for group_id in await self.queries.groups(media.connection_id):
            context = await self.reader.load(
                channel_id=media.channel_id, group_id=group_id
            )
            draft = await self.drafts.prepare(
                context=context,
                overrides=context.state.overrides,
                as_of=self.clock.now(),
            )
            if draft.export_blockers:
                continue
            platform = self.platforms.get(context.channel.platform_kind)
            if any(
                image.file_id.uuid == media.file_id
                and platform.media_metadata_fingerprint(image.alt)
                == media.metadata_fingerprint
                for target in draft.prepared.preparation.targets
                for content in target.content
                for image in content.gallery or ()
            ):
                return True
        return False
