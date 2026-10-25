from typing import Literal, Self
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from src.modules.crm.application.basket.values import BasketInput, BasketLineInput
from src.modules.crm.application.contact_point.dto import ContactPointDraftDTO


class StrictRequest(BaseModel):
    """Транспорт с явным отклонением неизвестных полей."""

    model_config = ConfigDict(extra="forbid")


class BasketLineRequest(StrictRequest):
    """Транспортная коммерческая строка с десятичными строками."""

    id: UUID | None = None
    client_line_key: str | None = Field(default=None, max_length=100)
    catalog_item_id: UUID | None = None
    name: str = Field(max_length=255)
    kind: Literal["product", "service"]
    sku: str | None = Field(default=None, max_length=128)
    quantity: str = Field(max_length=40)
    unit: str = Field(default="шт.", max_length=32)
    unit_price: str = Field(max_length=40)
    custom_fields: dict[str, str] = Field(default_factory=dict)

    def to_values(self) -> BasketLineInput:
        """Преобразует транспорт в явные прикладные значения."""
        values = self.model_dump()
        values["quantity"] = Decimal(self.quantity)
        values["unit_price"] = Decimal(self.unit_price)
        return BasketLineInput(**values)


class BasketRequest(StrictRequest):
    """Полная замена корзины; версию проверяет сценарий изменения."""

    currency: Literal["USD", "EUR", "UAH"]
    items: tuple[BasketLineRequest, ...] = Field(default=(), max_length=200)
    expected_revision: int | None = Field(default=None, ge=1)

    def to_values(self) -> BasketInput:
        """Преобразует строки без промежуточного float."""
        return BasketInput(
            self.currency,
            tuple(i.to_values() for i in self.items),
            self.expected_revision,
        )


class PointRequest(StrictRequest):
    """Данные собственной точки связи владельца."""

    value: str = Field(max_length=320)
    binding_id: UUID | None = None
    label_id: UUID | None = None
    country_code: str | None = None

    def to_values(self) -> ContactPointDraftDTO:
        """Сохраняет семантику нового и существующего binding."""
        return ContactPointDraftDTO(**self.model_dump())
