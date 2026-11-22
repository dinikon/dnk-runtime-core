from dataclasses import dataclass
from decimal import Decimal
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.feed_builder.domain.feed.validation import decimal
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

    def __post_init__(self) -> None:
        """Проверяет собственные типы без обращения к Catalog или часам."""
        if not isinstance(self.product_id, EntityIdVO) or (
            self.sku is not None and not isinstance(self.sku, str)
        ):
            raise InvalidFeedValueError(
                "Нужны идентификатор и строковый SKU выбранной позиции."
            )
        for value in (self.regular, self.sale, self.effective):
            if value is not None:
                decimal(value, label="Calculation input")

    def get(self, name: str) -> Decimal | str | EntityIdVO | None:
        """Различает отсутствующее значение и неизвестный параметр."""
        parameter_type(name)
        return {
            "price.regular": self.regular,
            "price.sale": self.sale,
            "price.effective": self.effective,
            "product.sku": self.sku,
            "product.id": self.product_id,
        }[name]
