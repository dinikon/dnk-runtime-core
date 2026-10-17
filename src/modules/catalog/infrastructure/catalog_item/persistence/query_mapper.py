from datetime import datetime
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
    CatalogItemDetailsAttributeDTO,
    CatalogItemDetailsMetadataDTO,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_items_publication_snapshot.dto import (
    CatalogItemPublicationDTO,
    CatalogItemPublicationImageDTO,
    CatalogItemPublicationGalleryDTO,
    CatalogItemPublicationAttributeDTO,
    CatalogItemPublicationMetadataDTO,
)


class CatalogItemQueryMapper:
    """Создаёт DTO конкретных сценариев из уже прочитанных значений без I/O."""

    @staticmethod
    def details(
        item: CatalogItemValuesSnapshot, locale: str, as_of: datetime
    ) -> CatalogItemDetailsDTO:
        """Собирает самостоятельный контракт details без восстановления агрегата."""
        computed = CatalogItemValuesPolicy.calculate(item, as_of)
        gallery = item.galleries.get(locale)
        return CatalogItemDetailsDTO(
            id=item.id.uuid,
            revision=item.revision,
            product_type_id=item.product_type_id.uuid,
            status=item.status,
            sku=item.sku,
            virtual=item.virtual,
            price_specification=item.price,
            price=computed.price,
            weight=item.weight,
            dimensions=item.dimensions,
            stock=item.stock,
            stock_status=computed.stock_status.value,
            backorders_allowed=computed.backorders_allowed,
            backordered=computed.backordered,
            available_for_sale=computed.available_for_sale,
            available_for_publication=computed.available_for_publication,
            content=(
                dict(item.translations[locale]) if locale in item.translations else None
            ),
            gallery=(
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
            ),
            attributes=tuple(
                CatalogItemDetailsAttributeDTO(
                    a.attribute_id.uuid,
                    tuple(o.uuid for o in a.option_ids),
                    a.visible,
                    a.position,
                )
                for a in item.attributes
            ),
            metadata=tuple(
                CatalogItemDetailsMetadataDTO(m.key, m.value_type, m.value, m.position)
                for m in item.metadata
            ),
            category_ids=tuple(i.uuid for i in item.category_ids),
            primary_category_id=(
                item.primary_category_id.uuid if item.primary_category_id else None
            ),
            tag_ids=tuple(i.uuid for i in item.tag_ids),
            created_at=item.created_at,
            updated_at=item.updated_at,
            created_by=item.created_by.uuid,
            updated_by=item.updated_by.uuid,
        )

    @staticmethod
    def publication(
        item: CatalogItemValuesSnapshot, locale: str, as_of: datetime
    ) -> CatalogItemPublicationDTO:
        """Собирает самостоятельный контракт publication без восстановления агрегата."""
        computed = CatalogItemValuesPolicy.calculate(item, as_of)
        gallery = item.galleries.get(locale)
        return CatalogItemPublicationDTO(
            id=item.id.uuid,
            revision=item.revision,
            product_type_id=item.product_type_id.uuid,
            status=item.status,
            sku=item.sku,
            virtual=item.virtual,
            price_specification=item.price,
            price=computed.price,
            weight=item.weight,
            dimensions=item.dimensions,
            stock=item.stock,
            stock_status=computed.stock_status.value,
            backorders_allowed=computed.backorders_allowed,
            backordered=computed.backordered,
            available_for_sale=computed.available_for_sale,
            available_for_publication=computed.available_for_publication,
            content=(
                dict(item.translations[locale]) if locale in item.translations else None
            ),
            gallery=(
                CatalogItemPublicationGalleryDTO(
                    tuple(
                        CatalogItemPublicationImageDTO(
                            i.id.uuid, i.file_id.uuid, i.position, i.alt, i.caption
                        )
                        for i in gallery.images
                    ),
                    gallery.primary_image_id.uuid if gallery.primary_image_id else None,
                )
                if gallery is not None
                else None
            ),
            attributes=tuple(
                CatalogItemPublicationAttributeDTO(
                    a.attribute_id.uuid,
                    tuple(o.uuid for o in a.option_ids),
                    a.visible,
                    a.position,
                )
                for a in item.attributes
            ),
            metadata=tuple(
                CatalogItemPublicationMetadataDTO(
                    m.key, m.value_type, m.value, m.position
                )
                for m in item.metadata
            ),
            category_ids=tuple(i.uuid for i in item.category_ids),
            primary_category_id=(
                item.primary_category_id.uuid if item.primary_category_id else None
            ),
            tag_ids=tuple(i.uuid for i in item.tag_ids),
            created_at=item.created_at,
            updated_at=item.updated_at,
            created_by=item.created_by.uuid,
            updated_by=item.updated_by.uuid,
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
            revision=item.revision,
            status=item.status,
            sku=item.sku,
            title=item.translations.get(locale, {}).get("name"),
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
            available_for_sale=computed.available_for_sale,
            weight=item.weight,
            dimensions=item.dimensions,
        )
