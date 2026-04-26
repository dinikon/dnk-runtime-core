from dataclasses import dataclass
from datetime import datetime
from typing import Self

from src.modules.inventory.domain.category.value_object import CategoryIdVO
from src.modules.inventory.domain.product.value_object import (
    ProductIdVO,
    ProductNameVO,
    SkuVO,
)


@dataclass(slots=True)
class ProductEntity:
    """Доменная сущность физического товара, который можно продать."""

    id: ProductIdVO
    created_at: datetime
    updated_at: datetime
    sku: SkuVO
    product_name: ProductNameVO
    description: str | None = None
    category_id: CategoryIdVO | None = None

    @classmethod
    def create(
        cls,
        *,
        id_: ProductIdVO,
        now: datetime,
        sku: str,
        product_name: str,
        description: str | None = None,
        category_id: CategoryIdVO | None = None,
    ) -> Self:
        """Создает товар с едиными created_at/updated_at и валидированными полями."""
        return cls(
            id=id_,
            created_at=now,
            updated_at=now,
            sku=SkuVO(sku),
            product_name=ProductNameVO(product_name),
            description=description,
            category_id=category_id,
        )

    def update(
        self,
        *,
        now: datetime,
        sku: str,
        product_name: str,
        description: str | None = None,
        category_id: CategoryIdVO | None = None,
    ) -> None:
        """Обновляет данные товара, если они изменились."""
        new_sku = SkuVO(sku)
        new_product_name = ProductNameVO(product_name)

        if (
            self.sku == new_sku
            and self.product_name == new_product_name
            and self.description == description
            and self.category_id == category_id
        ):
            return

        self.sku = new_sku
        self.product_name = new_product_name
        self.description = description
        self.category_id = category_id
        self.updated_at = now
