from decimal import Decimal, InvalidOperation, localcontext
from uuid import UUID
from pydantic import BaseModel, ConfigDict, StrictStr, field_validator


class AddItemPackagingRequest(BaseModel):
    """Принимает ручные параметры упаковки без идентификатора новой Entity."""

    model_config = ConfigDict(extra="forbid")
    packaging_type_id: UUID
    code: StrictStr
    name: StrictStr
    content_quantity: Decimal
    content_uom: StrictStr

    @field_validator("content_quantity", mode="before", json_schema_input_type=str)
    @classmethod
    def parse_quantity(cls, value: object) -> Decimal:
        """Разбирает конечный Decimal только из строки; положительность проверяет Domain."""
        if not isinstance(value, str):
            raise ValueError("Передайте количество содержимого строкой.")
        try:
            with localcontext():
                parsed = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("Некорректное количество содержимого.") from exc
        if not parsed.is_finite():
            raise ValueError("Количество содержимого должно быть конечным.")
        return parsed
