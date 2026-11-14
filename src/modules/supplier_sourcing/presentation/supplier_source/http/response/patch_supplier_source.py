from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierModelKey,
)
from typing import Self
from uuid import UUID
from pydantic import BaseModel
from src.modules.supplier_sourcing.domain.supplier_source.value_object.fulfillment_mode import (
    SupplierFulfillmentMode,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.stock_update_policy import (
    StaleStockBehavior,
    MissingSkuBehavior,
)
from src.modules.supplier_sourcing.application.supplier_source.command.update_supplier_source.dto import (
    UpdateSupplierSourceResultDTO,
)


class PatchSupplierStockUpdatePolicyResponse(BaseModel):
    """Описывает настройки актуальности в ответе patch."""

    ttl_seconds: int
    stale_behavior: StaleStockBehavior
    missing_sku_behavior: MissingSkuBehavior


class PatchSupplierSourceResponse(BaseModel):
    """HTTP-представление результата сценария patch."""

    id: UUID
    supplier_model_key: SupplierModelKey
    supplier_id: UUID
    supplier_name: str | None
    name: str
    external_warehouse_code: str | None
    fulfillment_modes: tuple[SupplierFulfillmentMode, ...]
    default_lead_time_seconds: int
    is_active: bool
    stock_update_policy: PatchSupplierStockUpdatePolicyResponse

    @classmethod
    def from_dto(cls, dto: UpdateSupplierSourceResultDTO) -> Self:
        """Явно преобразует результат Application в HTTP-контракт."""
        return cls(
            id=dto.id,
            supplier_model_key=dto.supplier_model_key,
            supplier_id=dto.supplier_id,
            supplier_name=dto.supplier_name,
            name=dto.name,
            external_warehouse_code=dto.external_warehouse_code,
            fulfillment_modes=dto.fulfillment_modes,
            default_lead_time_seconds=dto.default_lead_time_seconds,
            is_active=dto.is_active,
            stock_update_policy=PatchSupplierStockUpdatePolicyResponse(
                ttl_seconds=dto.stock_ttl_seconds,
                stale_behavior=dto.stale_behavior,
                missing_sku_behavior=dto.missing_sku_behavior,
            ),
        )
