import asyncio
from uuid import UUID
from src.modules.channels.application.external_publication.command.create_catalog_from_publication.command import (
    CreateCatalogFromPublicationCommand,
)
from src.modules.channels.application.external_publication.command.create_catalog_from_publication.dto import (
    CreateCatalogFromPublicationResultDTO,
)
from src.modules.channels.application.external_publication.catalog_details import (
    PublicationCreationSnapshot,
    PublicationDetails,
)
from src.modules.channels.application.external_publication.port.catalog_creation import (
    PublicationCreationReadPort,
    PublicationCatalogPort,
    PublicationImagesPort,
)
from src.modules.channels.application.external_publication.catalog_creation_error import (
    PublicationCatalogError,
    PublicationCatalogSkuRace,
)
from src.modules.channels.application.port.platform import PlatformRegistry
from src.modules.channels.application.catalog_binding.ports import BindingReadPort
from src.modules.channels.application.catalog_binding.writes import BindingWrites
from src.modules.channels.application.catalog_binding.views import BindingViews
from src.modules.channels.application.catalog_binding.contracts import BindingPairDTO
from src.modules.channels.domain.catalog_binding.value_object import (
    PublicationNode,
    BindingMode,
)
from src.modules.channels.domain.external_publication.catalog_creation import (
    PublicationCatalogPolicy,
)
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.shared.application.crypto.cipher import Cipher
from src.modules.shared.application.persistence.unit_of_work import UnitOfWorkProtocol
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CreateCatalogFromPublicationHandler:
    """Выполняет один HTTP процесс с сетью между короткими транзакциями."""

    def __init__(
        self,
        *,
        read: PublicationCreationReadPort,
        channels: ChannelRepositoryProtocol,
        platforms: PlatformRegistry,
        cipher: Cipher,
        catalog: PublicationCatalogPort,
        images: PublicationImagesPort,
        bindings: BindingReadPort,
        views: BindingViews,
        writes: BindingWrites,
        uow: UnitOfWorkProtocol,
        uuid: UUIdGeneratorProtocol,
        clock: ClockPort,
        max_images: int,
    ) -> None:
        """Получает порты; явный UoW нужен для освобождения транзакции до сети."""
        self.read, self.channels, self.platforms, self.cipher = (
            read,
            channels,
            platforms,
            cipher,
        )
        self.catalog, self.images, self.bindings, self.views, self.writes = (
            catalog,
            images,
            bindings,
            views,
            writes,
        )
        self.uow, self.uuid, self.clock, self.max_images = uow, uuid, clock, max_images

    async def _existing(
        self, snapshot: PublicationCreationSnapshot
    ) -> CreateCatalogFromPublicationResultDTO | None:
        """Повтор после потери ответа использует существующую привязку."""
        records, _ = await self.bindings.records(
            connection_id=snapshot.connection_id,
            publication_id=snapshot.root_id,
            limit=None,
        )
        if records:
            return CreateCatalogFromPublicationResultDTO(
                records[0].catalog_root_id, records[0].id, False
            )
        return None

    @staticmethod
    def _kind(snapshot: PublicationCreationSnapshot) -> str:
        """Делегирует правило канонического контейнера чистой Domain политике."""
        return PublicationCatalogPolicy().kind(
            platform=snapshot.platform,
            root_id=EntityIdVO(snapshot.root_id),
            nodes=tuple(
                PublicationNode(
                    EntityIdVO(p.id),
                    p.kind,
                    EntityIdVO(p.parent_id) if p.parent_id else None,
                )
                for p in snapshot.publications
            ),
        )

    @staticmethod
    def _require_details(
        snapshot: PublicationCreationSnapshot, details: PublicationDetails
    ) -> None:
        """Не создаёт связи по устаревшему или неполному составу семейства."""
        root = next(p for p in snapshot.publications if p.id == snapshot.root_id)
        PublicationCatalogPolicy().ensure_same_source(
            expected=tuple(
                (
                    p.resource_type,
                    p.external_id,
                    p.kind,
                    root.external_id if p.parent_id else None,
                )
                for p in snapshot.publications
            ),
            actual=tuple(
                (p.resource_type, p.external_id, p.kind, p.parent_external_id)
                for p in details.products
            ),
        )

    async def execute(
        self, command: CreateCatalogFromPublicationCommand
    ) -> CreateCatalogFromPublicationResultDTO:
        """Получает детали, переносит фотографии и атомарно создаёт товар со связью."""
        snapshot = await self.read.snapshot(command.channel_id, command.publication_id)
        existing = await self._existing(snapshot)
        if existing:
            return existing
        kind = self._kind(snapshot)
        await self.uow.commit()
        details = await self.platforms.get(snapshot.platform).get_details(
            config=snapshot.config,
            credentials=self.cipher.decrypt(snapshot.encrypted_credentials),
            publications=snapshot.publications,
        )
        self._require_details(snapshot, details)
        if any(len(p.image_urls) > self.max_images for p in details.products):
            raise PublicationCatalogError("publication_images_limit")
        root_id = self.uuid.new()
        images: dict[str, UUID] = {}
        warnings = list(details.warnings)
        urls = tuple(
            dict.fromkeys(url for p in details.products for url in p.image_urls)
        )
        downloaded = await asyncio.gather(
            *(self.images.download(root_id, url) for url in urls)
        )
        for url, (file_id, warning) in zip(urls, downloaded):
            if file_id:
                images[url] = file_id
            if warning:
                warnings.append(warning)
        for attempt in range(2):
            try:
                return await self._finish(
                    command,
                    snapshot,
                    details,
                    kind,
                    root_id,
                    images,
                    tuple(dict.fromkeys(warnings)),
                )
            except PublicationCatalogSkuRace:
                await self.uow.rollback()
                if attempt:
                    raise
        raise PublicationCatalogError("catalog_creation_failed")

    async def _finish(
        self,
        command: CreateCatalogFromPublicationCommand,
        snapshot: PublicationCreationSnapshot,
        details: PublicationDetails,
        kind: str,
        root_id: UUID,
        images: dict[str, UUID],
        warnings: tuple[str, ...],
    ) -> CreateCatalogFromPublicationResultDTO:
        """Повторно проверяет доступ и состав под блокировками до единственного commit."""
        await self.catalog.lock(command.tenant_id, root_id)
        channel = await self.channels.get(
            EntityIdVO(command.channel_id), for_update=True
        )
        if channel is None:
            raise PublicationCatalogError("channel_not_found")
        current = await self.read.snapshot(command.channel_id, command.publication_id)
        existing = await self._existing(current)
        if existing:
            return existing
        if (
            current.connection_id != snapshot.connection_id
            or current.config_revision != snapshot.config_revision
            or current.publications != snapshot.publications
        ):
            raise PublicationCatalogError(
                "publication_structure_changed", conflict=True
            )
        created = await self.catalog.create(
            tenant_id=command.tenant_id,
            actor_id=command.actor_id,
            root_id=root_id,
            details=details,
            platform=snapshot.platform,
            images=images,
        )
        root = next(p for p in details.products if p.parent_external_id is None)
        children = tuple(
            p for p in details.products if p.parent_external_id is not None
        )
        sellable = (
            ((root, *children) if snapshot.platform == "prom" else children)
            if kind == "variable"
            else (root,)
        )
        if len(created.position_ids) != len(sellable):
            raise PublicationCatalogError("catalog_creation_failed")
        identifiers = {
            (p.resource_type, p.external_id): p.id for p in snapshot.publications
        }
        pairs = tuple(
            BindingPairDTO(catalog_id, identifiers[(p.resource_type, p.external_id)])
            for p, catalog_id in zip(sellable, created.position_ids)
        )
        mode = (
            BindingMode.VARIABLE_TO_VARIABLE
            if kind == "variable"
            else BindingMode.SIMPLE_TO_SIMPLE
        )
        locale = next(
            (t.locale for t in root.translations if t.title is not None), "uk"
        )
        now = self.clock.now()
        preview = await self.views.preview(
            connection_id=snapshot.connection_id,
            platform=snapshot.platform,
            catalog_root_id=root_id,
            mode=mode,
            publication_root_id=snapshot.root_id,
            items=pairs,
            locale=locale,
            now=now,
        )
        group = await self.writes.create(
            tenant_id=command.tenant_id,
            channel_id=command.channel_id,
            catalog_root_id=root_id,
            mode=mode,
            publication_root_id=snapshot.root_id,
            items=pairs,
            catalog_token=preview.catalog_token,
            publication_token=preview.publication_token,
            actor_id=command.actor_id,
            now=now,
            locale=locale,
        )
        await self.uow.commit()
        return CreateCatalogFromPublicationResultDTO(
            created.root_id,
            group.id.uuid,
            True,
            tuple(dict.fromkeys((*warnings, *created.warnings))),
        )
