from decimal import Decimal, InvalidOperation, localcontext
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StrictStr, field_validator, model_validator
from pydantic.json_schema import SkipJsonSchema


class PatchItemPackagingRequest(BaseModel):
    """Принимает непустой набор изменений упаковки, отличая отсутствие поля от null."""

    model_config = ConfigDict(extra="forbid")
    packaging_type_id: UUID | SkipJsonSchema[None] = None
    code: StrictStr | SkipJsonSchema[None] = None
    name: StrictStr | SkipJsonSchema[None] = None
    content_quantity: Decimal | SkipJsonSchema[None] = None
    content_uom: StrictStr | SkipJsonSchema[None] = None

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

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        """Запрещает пустой PATCH и явный null для каждого переданного поля."""
        if not self.model_fields_set or any(
            getattr(self, field) is None for field in self.model_fields_set
        ):
            raise ValueError("Нужен непустой набор изменяемых полей без null.")
        return self
