from dataclasses import replace
from uuid import UUID
from sqlalchemy.exc import IntegrityError
from src.modules.catalog.application.catalog_item.publication_creation import (
    PublicationCatalogCreation,
    PublicationCatalogProductInput,
)
from src.modules.catalog.domain.error import CatalogError, CatalogConflictError
from src.modules.channels.application.external_publication.catalog_details import (
    PublicationDetails,
    PublicationProductDetails,
    CreatedPublicationCatalog,
)
from src.modules.channels.application.external_publication.catalog_creation_error import (
    PublicationCatalogError,
    PublicationCatalogSkuRace,
)


class CatalogPublicationGateway:
    """Переводит DTO Channels в публичные входы Catalog без импорта его Entity."""

    def __init__(self, catalog: PublicationCatalogCreation) -> None:
        """Получает интерфейс владельца на общей транзакции."""
        self.catalog = catalog

    async def lock(self, tenant_id: UUID, root_id: UUID) -> None:
        """Делегирует блокировку владельцу Catalog."""
        await self.catalog.lock(tenant_id, root_id)

    @staticmethod
    def _input(
        product: PublicationProductDetails, images: dict[str, UUID]
    ) -> PublicationCatalogProductInput:
        """Передаёт поддержанные значения без нативных атрибутов и внешних JSON."""
        translations = {
            t.locale: {
                k: v for k, v in (("title", t.title), ("body", t.body)) if v is not None
            }
            for t in product.translations
        }
        return PublicationCatalogProductInput(
            product.sku,
            translations,
            tuple(images[url] for url in product.image_urls if url in images),
            product.manage_stock,
            product.quantity,
            product.stock_status,
            product.backorders,
            product.virtual,
            product.weight,
            product.weight_unit,
            product.length,
            product.width,
            product.height,
            product.dimension_unit,
            product.regular_price,
            product.currency,
            product.sale_price,
            product.date_on_sale_from,
            product.date_on_sale_to,
        )

    async def create(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        root_id: UUID,
        details: PublicationDetails,
        platform: str,
        images: dict[str, UUID],
    ) -> CreatedPublicationCatalog:
        """Создаёт канонический контейнер и сохраняет порядок продаваемых позиций."""
        root = next(p for p in details.products if p.parent_external_id is None)
        children = tuple(
            p for p in details.products if p.parent_external_id is not None
        )
        variants = (
            ((root, *children) if platform == "prom" else children) if children else ()
        )
        container = (
            replace(
                root,
                sku=None,
                virtual=False,
                manage_stock=False,
                quantity=None,
                stock_status="in_stock",
                backorders="no",
                regular_price=None,
                currency=None,
                sale_price=None,
                date_on_sale_from=None,
                date_on_sale_to=None,
            )
            if platform == "prom" and children
            else root
        )
        try:
            result = await self.catalog.create(
                tenant_id=tenant_id,
                actor_id=actor_id,
                root_id=root_id,
                kind="variable" if children else "simple",
                root=self._input(container, images),
                variants=tuple(self._input(v, images) for v in variants),
            )
        except IntegrityError as error:
            cause = getattr(error.orig, "__cause__", None) or error.orig
            if getattr(cause, "constraint_name", None) == "uq_catalog_item_sku":
                raise PublicationCatalogSkuRace(
                    "catalog_sku_changed", conflict=True
                ) from error
            raise
        except CatalogConflictError as error:
            if error.fields == ("sku",):
                raise PublicationCatalogSkuRace(
                    "catalog_sku_changed", conflict=True
                ) from error
            raise PublicationCatalogError(
                "catalog_values_invalid", conflict=True
            ) from error
        except CatalogError as error:
            raise PublicationCatalogError("catalog_values_invalid") from error
        except (ValueError, ArithmeticError):
            raise PublicationCatalogError("catalog_values_invalid") from None
        return CreatedPublicationCatalog(
            result.root_id, result.position_ids, result.warnings
        )
