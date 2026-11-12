from decimal import Decimal, InvalidOperation, localcontext
from pydantic import BaseModel, ConfigDict, StrictStr, field_validator

from typing import Self
from pydantic import model_validator
from pydantic.json_schema import SkipJsonSchema

from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)


class PatchInventoryItemQuantityRulesRequest(BaseModel):
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


class PatchInventoryItemRequest(BaseModel):
    """Описывает частичное изменение редактируемых данных существующей позиции."""

    model_config = ConfigDict(extra="forbid")
    sku: StrictStr | SkipJsonSchema[None] = None
    base_uom: StrictStr | SkipJsonSchema[None] = None
    quantity_rules: PatchInventoryItemQuantityRulesRequest | SkipJsonSchema[None] = None
    tracking_mode: TrackingMode | SkipJsonSchema[None] = None
    expiration_mode: ExpirationMode | SkipJsonSchema[None] = None
    barcodes: list[StrictStr] | SkipJsonSchema[None] = None

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        """Отличает отсутствие поля от null и отклоняет пустой PATCH."""
        fields = self.model_fields_set
        if not fields or any(getattr(self, field) is None for field in fields):
            raise ValueError("Нужен непустой набор изменяемых полей без null.")
        return self
