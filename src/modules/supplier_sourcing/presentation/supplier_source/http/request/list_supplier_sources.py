from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierModelKey,
)

from typing import Self
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from src.modules.supplier_sourcing.domain.supplier_source.value_object.fulfillment_mode import (
    SupplierFulfillmentMode,
)


class ListSupplierSourcesRequest(BaseModel):
    """Проверяет query-параметры, включая полную идентичность выбранного поставщика."""

    model_config = ConfigDict(extra="forbid")
    supplier_model_key: SupplierModelKey | None = None
    supplier_id: UUID | None = None
    search: str | None = None
    is_active: bool | None = None
    fulfillment_mode: SupplierFulfillmentMode | None = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=100)

    @model_validator(mode="after")
    def require_supplier_type(self) -> Self:
        """Требует тип при фильтрации по UUID; один тип фильтрует все записи этого типа."""
        if self.supplier_id is not None and self.supplier_model_key is None:
            raise ValueError("Для supplier_id необходим supplier_model_key.")
        return self
