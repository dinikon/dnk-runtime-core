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
from pydantic.json_schema import SkipJsonSchema
from src.modules.supplier_sourcing.domain.supplier_source.value_object.fulfillment_mode import (
    SupplierFulfillmentMode,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.stock_update_policy import (
    StaleStockBehavior,
    MissingSkuBehavior,
)


class PatchSupplierStockUpdatePolicyRequest(BaseModel):
    """Передаёт целую политику актуальности с длительностью в секундах."""

    model_config = ConfigDict(extra="forbid")
    ttl_seconds: Annotated[StrictInt, Field(ge=1, le=86399999999999)]
    stale_behavior: StaleStockBehavior
    missing_sku_behavior: MissingSkuBehavior


class PatchSupplierSourceRequest(BaseModel):
    """Явный HTTP-контракт сценария patch источника."""

    model_config = ConfigDict(extra="forbid")
    name: StrictStr | SkipJsonSchema[None] = None
    external_warehouse_code: StrictStr | None = None
    fulfillment_modes: list[SupplierFulfillmentMode] | SkipJsonSchema[None] = None
    default_lead_time_seconds: (
        Annotated[StrictInt, Field(ge=0, le=86399999999999)] | SkipJsonSchema[None]
    ) = None
    is_active: StrictBool | SkipJsonSchema[None] = None
    stock_update_policy: (
        PatchSupplierStockUpdatePolicyRequest | SkipJsonSchema[None]
    ) = None

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        """Не допускает пустой PATCH и null обязательных полей."""
        if not self.model_fields_set or any(
            getattr(self, field) is None
            for field in self.model_fields_set
            if field != "external_warehouse_code"
        ):
            raise ValueError(
                "Нужны изменяемые поля; null допустим только для внешнего кода."
            )
        if self.fulfillment_modes is not None and len(
            set(self.fulfillment_modes)
        ) != len(self.fulfillment_modes):
            raise ValueError("Режимы исполнения не должны повторяться.")
        return self
