from typing import Annotated, Self
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictStr,
    StrictBool,
    StrictInt,
    model_validator,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.fulfillment_mode import (
    SupplierFulfillmentMode,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.stock_update_policy import (
    StaleStockBehavior,
    MissingSkuBehavior,
)


class PutSupplierStockUpdatePolicyRequest(BaseModel):
    """Передаёт целую политику актуальности с длительностью в секундах."""

    model_config = ConfigDict(extra="forbid")
    ttl_seconds: Annotated[StrictInt, Field(ge=1, le=86399999999999)]
    stale_behavior: StaleStockBehavior
    missing_sku_behavior: MissingSkuBehavior


class PutSupplierSourceRequest(BaseModel):
    """Явный HTTP-контракт сценария put источника."""

    model_config = ConfigDict(extra="forbid")
    name: StrictStr
    external_warehouse_code: StrictStr | None
    fulfillment_modes: list[SupplierFulfillmentMode]
    default_lead_time_seconds: Annotated[StrictInt, Field(ge=0, le=86399999999999)]
    stock_update_policy: PutSupplierStockUpdatePolicyRequest
    is_active: StrictBool

    @model_validator(mode="after")
    def require_unique_modes(self) -> Self:
        """Отклоняет дубликаты вместо неявного удаления при преобразовании в набор."""
        if len(set(self.fulfillment_modes)) != len(self.fulfillment_modes):
            raise ValueError("Режимы исполнения не должны повторяться.")
        return self
