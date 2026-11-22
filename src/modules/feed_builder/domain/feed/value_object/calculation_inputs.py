from dataclasses import dataclass
from decimal import Decimal
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError
from src.modules.feed_builder.domain.feed.calculation.parameters import parameter_type


@dataclass(frozen=True, slots=True)
class CalculationInputsVO:
    """Хранит неизменяемые значения выбранной продаваемой позиции без валюты и I/O."""

    product_id: EntityIdVO
    sku: str | None
    regular: Decimal | None
    sale: Decimal | None
    effective: Decimal | None
    purchase: Decimal | None = None
    category_ids: tuple[EntityIdVO, ...] = ()

    def __post_init__(self) -> None:
        """Проверяет собственные типы без обращения к Catalog или часам."""
        if not isinstance(self.product_id, EntityIdVO) or (
            self.sku is not None and not isinstance(self.sku, str)
        ):
            raise InvalidFeedValueError(
                "Нужны идентификатор и строковый SKU выбранной позиции."
            )
        for value in (self.regular, self.sale, self.effective, self.purchase):
            if value is not None and (
                not isinstance(value, Decimal) or not value.is_finite()
            ):
                raise InvalidFeedValueError(
                    "Входная цена должна быть конечным Decimal."
                )

        if not isinstance(self.category_ids, tuple) or any(
            not isinstance(category, EntityIdVO) for category in self.category_ids
        ):
            raise InvalidFeedValueError("Нужен набор ID категорий Catalog.")

    def get(
        self, name: str
    ) -> Decimal | str | EntityIdVO | tuple[EntityIdVO, ...] | None:
        """Различает отсутствующее значение и неизвестный параметр."""
        parameter_type(name)
        return {
            "price.regular": self.regular,
            "price.sale": self.sale,
            "price.effective": self.effective,
            "product.sku": self.sku,
            "product.id": self.product_id,
            "price.purchase": self.purchase,
            "product.category_ids": self.category_ids,
        }[name]
