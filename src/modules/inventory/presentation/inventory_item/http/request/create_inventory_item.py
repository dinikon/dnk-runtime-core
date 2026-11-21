from decimal import Decimal, InvalidOperation, localcontext
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictStr,
    field_validator,
    model_validator,
)
from pydantic.json_schema import SkipJsonSchema

from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)


class CreateInventoryItemQuantityRulesRequest(BaseModel):
    """Принимает явно заданный шаг строкой для точного Decimal-преобразования."""

    model_config = ConfigDict(extra="forbid")

    step: Decimal

    @field_validator("step", mode="before", json_schema_input_type=str)
    @classmethod
    def parse_step(cls, value: object) -> Decimal:
        """Отклоняет JSON-числа, чтобы шаг не проходил через двоичную дробь."""
        if not isinstance(value, str):
            raise ValueError("Передайте шаг количества строкой.")
        try:
            with localcontext():
                parsed = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("Некорректный десятичный шаг количества.") from exc
        if not parsed.is_finite():
            raise ValueError("Шаг количества должен быть конечным числом.")
        return parsed


class CreateInventoryItemRequest(BaseModel):
    """Описывает тело создания позиции без упаковок и клиентских UUID."""

    model_config = ConfigDict(extra="forbid")

    sku: StrictStr
    base_uom: StrictStr | SkipJsonSchema[None] = None
    quantity_rules: CreateInventoryItemQuantityRulesRequest | SkipJsonSchema[None] = (
        None
    )
    tracking_mode: TrackingMode | SkipJsonSchema[None] = None
    expiration_mode: ExpirationMode | SkipJsonSchema[None] = None
    barcodes: list[StrictStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def reject_explicit_null(self) -> Self:
        """Разрешает отсутствие настроек и отклоняет явный null вместо значения."""
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError(
                "Пропустите необязательное поле или передайте значение без null."
            )
        return self
