from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import TypeAlias
from uuid import UUID

from modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.domain.error import (
    ProductRowFieldMustBeNonNegativeError,
    ProductRowMeasureCodeRequiredError,
    ProductRowMeasureNameRequiredError,
    ProductRowProductNameRequiredError,
    ProductRowQuantityMustBePositiveError,
)
from src.modules.crm.domain.product_row.value_objects import (
    ProductRowDiscountTypeVO,
    ProductRowEntityIdVO,
    ProductRowIdVO,
)

DecimalLike: TypeAlias = Decimal | int | float | str
ProductIdLike: TypeAlias = EntityIdVO | UUID | str | None


@dataclass(slots=True)
class ProductRowEntity:
    id: ProductRowIdVO
    entity_id: ProductRowEntityIdVO
    entity_uuid: EntityIdVO
    product_id: EntityIdVO | None
    product_name: str
    price: Decimal
    price_account: Decimal
    price_exclusive: Decimal
    price_netto: Decimal
    price_brutto: Decimal
    quantity: Decimal
    discount_type_id: ProductRowDiscountTypeVO
    discount_rate: Decimal
    discount_sum: Decimal
    tax_rate: Decimal
    tax_included: bool
    customized: bool
    measure_code: str
    measure_name: str
    sort: int

    @classmethod
    def create(
        cls,
        *,
        entity_id: ProductRowEntityIdVO,
        entity_uuid: EntityIdVO,
        product_name: str,
        product_id: ProductIdLike = None,
        price: DecimalLike = 0,
        price_account: DecimalLike = 0,
        price_exclusive: DecimalLike = 0,
        price_netto: DecimalLike = 0,
        price_brutto: DecimalLike = 0,
        quantity: DecimalLike = 1,
        discount_type_id: (
            ProductRowDiscountTypeVO | str
        ) = ProductRowDiscountTypeVO.PERCENT,
        discount_rate: DecimalLike = 0,
        discount_sum: DecimalLike = 0,
        tax_rate: DecimalLike = 0,
        tax_included: bool = False,
        customized: bool = False,
        measure_code: str = "pcs",
        measure_name: str = "pcs",
        sort: int = 0,
    ) -> "ProductRowEntity":
        normalized_product_name = product_name.strip()
        if not normalized_product_name:
            raise ProductRowProductNameRequiredError()

        normalized_measure_code = measure_code.strip()
        if not normalized_measure_code:
            raise ProductRowMeasureCodeRequiredError()

        normalized_measure_name = measure_name.strip()
        if not normalized_measure_name:
            raise ProductRowMeasureNameRequiredError()

        normalized_sort = cls._normalize_non_negative_int(sort=sort, field_name="sort")
        normalized_product_id = cls._normalize_product_id(product_id)
        normalized_discount_type = cls._normalize_discount_type(discount_type_id)

        return cls(
            id=ProductRowIdVO.new(),
            entity_id=entity_id,
            entity_uuid=entity_uuid,
            product_id=normalized_product_id,
            product_name=normalized_product_name,
            price=cls._normalize_non_negative_decimal(price=price, field_name="price"),
            price_account=cls._normalize_non_negative_decimal(
                price=price_account,
                field_name="price_account",
            ),
            price_exclusive=cls._normalize_non_negative_decimal(
                price=price_exclusive,
                field_name="price_exclusive",
            ),
            price_netto=cls._normalize_non_negative_decimal(
                price=price_netto,
                field_name="price_netto",
            ),
            price_brutto=cls._normalize_non_negative_decimal(
                price=price_brutto,
                field_name="price_brutto",
            ),
            quantity=cls._normalize_positive_decimal(quantity=quantity),
            discount_type_id=normalized_discount_type,
            discount_rate=cls._normalize_non_negative_decimal(
                price=discount_rate,
                field_name="discount_rate",
            ),
            discount_sum=cls._normalize_non_negative_decimal(
                price=discount_sum,
                field_name="discount_sum",
            ),
            tax_rate=cls._normalize_non_negative_decimal(
                price=tax_rate,
                field_name="tax_rate",
            ),
            tax_included=tax_included,
            customized=customized,
            measure_code=normalized_measure_code,
            measure_name=normalized_measure_name,
            sort=normalized_sort,
        )

    def assign_owner(
        self,
        *,
        entity_id: ProductRowEntityIdVO,
        entity_uuid: EntityIdVO,
    ) -> None:
        self.entity_id = entity_id
        self.entity_uuid = entity_uuid

    def clone_for_owner(
        self,
        *,
        entity_id: ProductRowEntityIdVO,
        entity_uuid: EntityIdVO,
    ) -> "ProductRowEntity":
        return ProductRowEntity.create(
            entity_id=entity_id,
            entity_uuid=entity_uuid,
            product_id=self.product_id,
            product_name=self.product_name,
            price=self.price,
            price_account=self.price_account,
            price_exclusive=self.price_exclusive,
            price_netto=self.price_netto,
            price_brutto=self.price_brutto,
            quantity=self.quantity,
            discount_type_id=self.discount_type_id,
            discount_rate=self.discount_rate,
            discount_sum=self.discount_sum,
            tax_rate=self.tax_rate,
            tax_included=self.tax_included,
            customized=self.customized,
            measure_code=self.measure_code,
            measure_name=self.measure_name,
            sort=self.sort,
        )

    @staticmethod
    def _normalize_product_id(product_id: ProductIdLike) -> EntityIdVO | None:
        if product_id is None:
            return None
        if isinstance(product_id, EntityIdVO):
            return product_id
        return EntityIdVO.from_value(product_id)

    @staticmethod
    def _normalize_discount_type(
        discount_type_id: ProductRowDiscountTypeVO | str,
    ) -> ProductRowDiscountTypeVO:
        if isinstance(discount_type_id, ProductRowDiscountTypeVO):
            return discount_type_id
        return ProductRowDiscountTypeVO(discount_type_id)

    @staticmethod
    def _normalize_non_negative_decimal(
        *,
        price: DecimalLike,
        field_name: str,
    ) -> Decimal:
        normalized = ProductRowEntity._to_decimal(price=price, field_name=field_name)
        if normalized < Decimal("0"):
            raise ProductRowFieldMustBeNonNegativeError(field_name)
        return normalized

    @staticmethod
    def _normalize_positive_decimal(*, quantity: DecimalLike) -> Decimal:
        normalized = ProductRowEntity._to_decimal(price=quantity, field_name="quantity")
        if normalized <= Decimal("0"):
            raise ProductRowQuantityMustBePositiveError()
        return normalized

    @staticmethod
    def _normalize_non_negative_int(*, sort: int, field_name: str) -> int:
        if sort < 0:
            raise ProductRowFieldMustBeNonNegativeError(field_name)
        return sort

    @staticmethod
    def _to_decimal(*, price: DecimalLike, field_name: str) -> Decimal:
        try:
            normalized = Decimal(str(price))
        except (InvalidOperation, ValueError):
            raise ProductRowFieldMustBeNonNegativeError(field_name) from None

        if not normalized.is_finite():
            raise ProductRowFieldMustBeNonNegativeError(field_name)
        return normalized


__all__ = ["ProductRowEntity"]
