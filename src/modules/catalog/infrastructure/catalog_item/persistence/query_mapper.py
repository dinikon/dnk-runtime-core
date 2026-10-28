from dataclasses import replace
from src.modules.catalog.domain.catalog_item.value_object.kind import CatalogItemKind
from src.modules.catalog.domain.catalog_item.policy.variant_values import (
    effective_variant,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_item.dto import (
    CatalogItemSourcesDTO,
)
from datetime import datetime
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery
from src.modules.catalog.domain.catalog_item.value_object.snapshot import (
    CatalogItemValuesSnapshot,
)
from src.modules.catalog.domain.catalog_item.policy.values import (
    CatalogItemValuesPolicy,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_items.row_dto import (
    CatalogItemListRowDTO,
    CatalogItemListImageDTO,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_item.dto import (
    CatalogItemDetailsDTO,
    CatalogItemDetailsImageDTO,
    CatalogItemDetailsGalleryDTO,
)


class CatalogItemQueryMapper:
    """Создаёт DTO конкретных сценариев из уже прочитанных значений без I/O."""

    @staticmethod
    def details(
        item: CatalogItemValuesSnapshot,
        locale: str,
        as_of: datetime,
        own: CatalogItemValuesSnapshot | None = None,
        sources: CatalogItemSourcesDTO | None = None,
    ) -> CatalogItemDetailsDTO:
        """Собирает самостоятельный контракт details без восстановления агрегата."""
        computed = CatalogItemValuesPolicy.calculate(item, as_of)
        original = own or item
        gallery = original.galleries.get(locale)
        effective_gallery = item.galleries.get(locale)
        return CatalogItemDetailsDTO(
            id=item.id.uuid,
            product_type_id=item.product_type_id.uuid,
            status=original.status,
            sku=item.sku,
            virtual=item.virtual,
            price_specification=item.price,
            price=computed.price,
            weight=original.weight,
            dimensions=original.dimensions,
            stock=original.stock,
            stock_status=computed.stock_status.value,
            backorders_allowed=computed.backorders_allowed,
            backordered=computed.backordered,
            available_for_sale=computed.available_for_sale
            and item.kind is not CatalogItemKind.VARIABLE,
            available_for_publication=computed.available_for_publication,
            content=(
                dict(original.translations[locale])
                if locale in original.translations
                else None
            ),
            gallery=(
                CatalogItemDetailsGalleryDTO(
                    tuple(
                        (
                            CatalogItemDetailsImageDTO(
                                i.id.uuid, i.file_id.uuid, i.position, i.alt, i.caption
                            )
                            for i in gallery.images
                        )
                    ),
                    gallery.primary_image_id.uuid if gallery.primary_image_id else None,
                )
                if gallery is not None
                else None
            ),
            created_at=item.created_at,
            updated_at=item.updated_at,
            created_by=item.created_by.uuid,
            updated_by=item.updated_by.uuid,
            kind=original.kind.value,
            parent_id=original.parent_id.uuid if original.parent_id else None,
            stock_source=(
                "parent" if sources and sources.stock != original.id.uuid else "own"
            ),
            effective_content=(
                dict(item.translations[locale]) if locale in item.translations else None
            ),
            effective_gallery=CatalogItemQueryMapper.gallery(effective_gallery),
            effective_stock=item.stock,
            effective_weight=item.weight,
            effective_dimensions=item.dimensions,
            sources=sources
            or CatalogItemSourcesDTO(
                item.id.uuid if "title" in item.translations.get(locale, {}) else None,
                item.id.uuid if "body" in item.translations.get(locale, {}) else None,
                item.id.uuid if effective_gallery is not None else None,
                item.id.uuid if item.weight is not None else None,
                item.id.uuid if item.dimensions is not None else None,
                item.id.uuid,
            ),
        )

    @staticmethod
    def list_row(
        item: CatalogItemValuesSnapshot, locale: str, as_of: datetime
    ) -> CatalogItemListRowDTO:
        """Создаёт компактную строку списка с ценой и главным изображением."""
        computed = CatalogItemValuesPolicy.calculate(item, as_of)
        gallery = item.galleries.get(locale)
        image = (
            next((i for i in gallery.images if i.id == gallery.primary_image_id), None)
            if gallery
            else None
        )
        return CatalogItemListRowDTO(
            id=item.id.uuid,
            status=item.status,
            sku=item.sku,
            title=item.translations.get(locale, {}).get("title"),
            price=computed.price,
            currency=item.price.currency if item.price else None,
            stock_status=computed.stock_status.value,
            primary_image=(
                CatalogItemListImageDTO(
                    image.id.uuid,
                    image.file_id.uuid,
                    image.position,
                    image.alt,
                    image.caption,
                )
                if image
                else None
            ),
            available_for_sale=computed.available_for_sale
            and item.kind is not CatalogItemKind.VARIABLE,
            weight=item.weight,
            dimensions=item.dimensions,
            kind=item.kind.value,
            parent_id=item.parent_id.uuid if item.parent_id else None,
        )

    @staticmethod
    def gallery(
        gallery: CatalogItemGallery | None,
    ) -> CatalogItemDetailsGalleryDTO | None:
        """Создаёт публичное назначение изображений без файловых запросов."""
        return (
            CatalogItemDetailsGalleryDTO(
                tuple(
                    CatalogItemDetailsImageDTO(
                        i.id.uuid, i.file_id.uuid, i.position, i.alt, i.caption
                    )
                    for i in gallery.images
                ),
                gallery.primary_image_id.uuid if gallery.primary_image_id else None,
            )
            if gallery is not None
            else None
        )

    @staticmethod
    def variant(
        parent: CatalogItemValuesSnapshot,
        own: CatalogItemValuesSnapshot,
        locale: str,
        as_of: datetime,
    ) -> CatalogItemDetailsDTO:
        """Разделяет собственные значения, эффективную проекцию и её источники."""
        resolved = effective_variant(parent, own, locale)
        sources = CatalogItemSourcesDTO(
            resolved.title_source_id.uuid if resolved.title_source_id else None,
            resolved.body_source_id.uuid if resolved.body_source_id else None,
            resolved.gallery_source_id.uuid if resolved.gallery_source_id else None,
            resolved.weight_source_id.uuid if resolved.weight_source_id else None,
            (
                resolved.dimensions_source_id.uuid
                if resolved.dimensions_source_id
                else None
            ),
            resolved.stock_source_id.uuid,
        )
        return CatalogItemQueryMapper.details(
            resolved.values, locale, as_of, own, sources
        )

    @staticmethod
    def family_details(
        item: CatalogItemDetailsDTO,
        children: tuple[CatalogItemValuesSnapshot, ...],
        as_of: datetime,
    ) -> CatalogItemDetailsDTO:
        """Вычисляет диапазон без пересчёта валют и продажи контейнера."""
        if item.kind != "variable":
            return item
        prices = [
            v.price.at(as_of)
            for v in children
            if v.status.value == "active" and v.price is not None
        ]
        currencies = {
            v.price.currency
            for v in children
            if v.status.value == "active" and v.price is not None
        }
        return replace(
            item,
            variant_count=len(children),
            min_price=min(prices) if prices and len(currencies) == 1 else None,
            max_price=max(prices) if prices and len(currencies) == 1 else None,
            currency=next(iter(currencies)) if len(currencies) == 1 else None,
            mixed_currencies=len(currencies) > 1,
            available_for_publication=item.status.value == "active"
            and any(v.status.value != "archived" for v in children),
        )
