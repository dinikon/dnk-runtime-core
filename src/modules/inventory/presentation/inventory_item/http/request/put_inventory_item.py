from decimal import Decimal, InvalidOperation, localcontext
from pydantic import BaseModel, ConfigDict, StrictStr, field_validator

from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)


class PutInventoryItemQuantityRulesRequest(BaseModel):
    """Принимает явно заданный шаг количества строкой."""

    model_config = ConfigDict(extra="forbid")
    step: Decimal

    @field_validator("step", mode="before", json_schema_input_type=str)
    @classmethod
    def parse_step(cls, value: object) -> Decimal:
        """Разбирает конечный Decimal без изменения контекста вызывающего кода."""
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


class PutInventoryItemRequest(BaseModel):
    """Описывает полную замену редактируемых данных существующей позиции."""

    model_config = ConfigDict(extra="forbid")
    sku: StrictStr
    base_uom: StrictStr
    quantity_rules: PutInventoryItemQuantityRulesRequest
    tracking_mode: TrackingMode
    expiration_mode: ExpirationMode
    barcodes: list[StrictStr]
