from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.domain.sales_error import SalesError


@dataclass(slots=True)
class BasketItem:
    """Коммерческая строка, принадлежащая только Basket."""

    id: EntityIdVO
    name: str
    kind: str
    catalog_item_id: EntityIdVO | None
    sku: str | None
    quantity: Decimal
    unit: str
    unit_price: Decimal
    custom_fields: dict[str, str]

    @classmethod
    def create(
        cls,
        *,
        item_id: EntityIdVO,
        name: str,
        kind: str,
        quantity: Decimal,
        unit_price: Decimal,
        unit: str = "шт.",
        catalog_item_id: EntityIdVO | None = None,
        sku: str | None = None,
        custom_fields: dict[str, str] | None = None,
    ) -> Self:
        """Создаёт проверенную строку с точными десятичными значениями."""
        name = name.strip()
        unit = unit.strip()
        fields = dict(custom_fields or {})
        if (
            not name
            or len(name) > 255
            or not unit
            or len(unit) > 32
            or kind not in ("product", "service")
        ):
            raise SalesError("Некорректные название, единица или тип позиции.")
        for value in (quantity, unit_price):
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or abs(value) > Decimal("999999999999.999999")
                or value.as_tuple().exponent < -6
            ):
                raise SalesError(
                    "Количество и цена: конечные десятичные значения, до 6 знаков."
                )
        if quantity <= 0 or unit_price < 0:
            raise SalesError(
                "Количество должно быть положительным, цена неотрицательной."
            )
        if len(fields) > 20 or any(
            not k.strip() or len(k) > 100 or len(v) > 1000 for k, v in fields.items()
        ):
            raise SalesError("Некорректные дополнительные поля позиции.")
        if sku is not None and len(sku) > 128:
            raise SalesError("Артикул слишком длинный.")
        return cls(
            EntityIdVO.from_value(item_id),
            name,
            kind,
            EntityIdVO.from_value(catalog_item_id) if catalog_item_id else None,
            sku,
            quantity,
            unit,
            unit_price,
            fields,
        )

    @classmethod
    def restore(cls, **values: object) -> Self:
        """Восстанавливает строку через ту же проверенную фабрику."""
        return cls.create(**values)

    @property
    def total(self) -> Decimal:
        """Округляет стоимость строки до денежной точности."""
        with localcontext() as context:
            context.prec = 40
            return (self.quantity * self.unit_price).quantize(
                Decimal(".01"), rounding=ROUND_HALF_UP
            )
