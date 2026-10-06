from src.modules.catalog.domain.product.aggregate import Product, ProductVariant
from src.modules.catalog.domain.product.value_object.content import ProductContentVO


class ProductMapper:
    """Явные значения вставки и восстановления агрегата."""

    @staticmethod
    def product_values(product: Product) -> dict[str, object]:
        return dict(
            id=product.id.uuid,
            kind=product.kind.value,
            product_type_id=product.product_type_id.uuid,
            created_at=product.created_at,
            updated_at=product.updated_at,
            created_by=product.created_by.uuid,
            updated_by=product.updated_by.uuid,
        )

    @staticmethod
    def variant_values(product: Product, variant: ProductVariant) -> dict[str, object]:
        return dict(
            id=variant.id.uuid,
            product_id=product.id.uuid,
            sku_id=variant.sku_id.uuid,
        )

    @staticmethod
    def content_values(product_id, content: ProductContentVO) -> dict[str, object]:
        return {"product_id": product_id, "locale_code": content.locale.value}
