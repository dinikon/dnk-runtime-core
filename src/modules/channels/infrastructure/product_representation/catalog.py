from datetime import datetime
from uuid import UUID

from src.modules.catalog.application.catalog_item.bindings_facade import (
    CatalogBindingsFacade,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_item.dto import (
    CatalogItemDetailsDTO,
)
from src.modules.channels.application.product_representation.contracts import (
    RepresentationCatalogFamily,
)
from src.modules.channels.domain.product_representation.value_object import (
    CatalogContentSnapshot,
    ContentImage,
    ContentOrigin,
    ContentOrigins,
    FieldOrigin,
    LocalizedContent,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class RepresentationCatalogGateway:
    """Переводит публичный многоязычный снимок Catalog в собственные типы Channels."""

    def __init__(self, facade: CatalogBindingsFacade) -> None:
        """Использует контракт владельца Catalog на той же сессии UoW."""
        self._facade = facade

    async def family(
        self, *, root_id: UUID, locales: tuple[str, ...], as_of: datetime
    ) -> RepresentationCatalogFamily | None:
        """Читает все позиции batch по локалям, без запросов по каждой вариации."""
        snapshots = await self._facade.families_for_locales(
            identifiers=(root_id,), locales=locales, as_of=as_of
        )
        if not snapshots:
            return None
        root = snapshots[0].root
        content: dict[UUID, list[LocalizedContent]] = {}
        for snapshot in snapshots:
            for position in (snapshot.root, *snapshot.variants):
                content.setdefault(position.id, []).append(
                    self._content(position, snapshot.locale)
                )
        prepared_root = CatalogContentSnapshot(
            EntityIdVO(root.id), root.kind, tuple(content[root.id])
        )
        positions = (
            tuple(
                CatalogContentSnapshot(
                    EntityIdVO(position.id), position.kind, tuple(content[position.id])
                )
                for position in snapshots[0].variants
            )
            if root.kind == "variable"
            else (prepared_root,)
        )
        return RepresentationCatalogFamily(prepared_root, positions)

    @staticmethod
    def _origin(*, position_id: UUID, source_id: UUID | None) -> FieldOrigin:
        """Сохраняет отсутствие источника даже при явно пустом значении поля."""
        if source_id is None:
            return FieldOrigin(ContentOrigin.MISSING, None)
        return FieldOrigin(
            (
                ContentOrigin.CATALOG
                if source_id == position_id
                else ContentOrigin.CATALOG_PARENT
            ),
            EntityIdVO(source_id),
        )

    @classmethod
    def _content(cls, position: CatalogItemDetailsDTO, locale: str) -> LocalizedContent:
        """Копирует только title/body/галерею; главное изображение помещает первым."""
        values = position.effective_content or {}
        gallery = position.effective_gallery
        images = (
            tuple(
                ContentImage(EntityIdVO(image.file_id), image.alt, image.caption)
                for image in sorted(
                    gallery.images,
                    key=lambda image: (
                        image.id != gallery.primary_image_id,
                        image.position,
                    ),
                )
            )
            if gallery is not None
            else None
        )
        sources = position.sources
        return LocalizedContent(
            locale=locale,
            title=values.get("title"),
            body=values.get("body"),
            gallery=images,
            origins=ContentOrigins(
                title=cls._origin(
                    position_id=position.id,
                    source_id=sources.title if sources else None,
                ),
                body=cls._origin(
                    position_id=position.id,
                    source_id=sources.body if sources else None,
                ),
                gallery=cls._origin(
                    position_id=position.id,
                    source_id=sources.gallery if sources else None,
                ),
            ),
        )
