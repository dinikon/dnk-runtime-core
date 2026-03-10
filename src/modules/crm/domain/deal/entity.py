from dataclasses import dataclass, field
from decimal import Decimal
from typing import Self
from uuid import UUID

from src.modules.crm.domain.deal.value_objects import DealIdVO, DealTitleVO
from src.modules.crm.domain.error import ProductRowNotFoundError
from src.modules.crm.domain.product_row.entity import ProductRowEntity
from src.modules.crm.domain.product_row.value_objects import (
    ProductRowDiscountTypeVO,
    ProductRowEntityIdVO,
    ProductRowIdVO,
)
from src.modules.crm.domain.shared.crm_entity_id import CrmEntityIdVO


@dataclass(slots=True)
class DealEntity:
    id: DealIdVO
    title: DealTitleVO
    product_rows: list[ProductRowEntity] = field(default_factory=list)

    @classmethod
    def create(cls, *, title: str) -> Self:
        return cls(id=DealIdVO.new(), title=DealTitleVO(title), product_rows=[])

    def rename(self, *, title: str) -> None:
        self.title = DealTitleVO(title)

    def add_product_row(
        self,
        *,
        product_name: str,
        product_id: CrmEntityIdVO | UUID | str | None = None,
        price: Decimal | int | float | str = 0,
        price_account: Decimal | int | float | str = 0,
        price_exclusive: Decimal | int | float | str = 0,
        price_netto: Decimal | int | float | str = 0,
        price_brutto: Decimal | int | float | str = 0,
        quantity: Decimal | int | float | str = 1,
        discount_type_id: ProductRowDiscountTypeVO | str = ProductRowDiscountTypeVO.PERCENT,
        discount_rate: Decimal | int | float | str = 0,
        discount_sum: Decimal | int | float | str = 0,
        tax_rate: Decimal | int | float | str = 0,
        tax_included: bool = False,
        customized: bool = False,
        measure_code: str = "pcs",
        measure_name: str = "pcs",
        sort: int = 0,
    ) -> ProductRowEntity:
        row = ProductRowEntity.create(
            entity_id=ProductRowEntityIdVO.deal(),
            entity_uuid=self.id,
            product_id=product_id,
            product_name=product_name,
            price=price,
            price_account=price_account,
            price_exclusive=price_exclusive,
            price_netto=price_netto,
            price_brutto=price_brutto,
            quantity=quantity,
            discount_type_id=discount_type_id,
            discount_rate=discount_rate,
            discount_sum=discount_sum,
            tax_rate=tax_rate,
            tax_included=tax_included,
            customized=customized,
            measure_code=measure_code,
            measure_name=measure_name,
            sort=sort,
        )
        self.product_rows.append(row)
        return row

    def remove_product_row(self, row_id: ProductRowIdVO) -> None:
        self.product_rows = [row for row in self.product_rows if row.id != row_id]

    def get_product_row(self, row_id: ProductRowIdVO) -> ProductRowEntity:
        for row in self.product_rows:
            if row.id == row_id:
                return row
        raise ProductRowNotFoundError(str(row_id))


__all__ = ["DealEntity"]
