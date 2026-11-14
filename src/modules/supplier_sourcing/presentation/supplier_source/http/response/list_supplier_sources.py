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
from src.modules.supplier_sourcing.application.supplier_source.query.list_supplier_sources.dto import (
    SupplierSourceListItemDTO,
)


class ListSupplierStockUpdatePolicyResponse(BaseModel):
    """Описывает настройки актуальности в ответе list."""

    ttl_seconds: int
    stale_behavior: StaleStockBehavior
    missing_sku_behavior: MissingSkuBehavior


class ListSupplierSourceItemResponse(BaseModel):
    """HTTP-представление результата сценария list."""

    id: UUID
    supplier_model_key: SupplierModelKey
    supplier_id: UUID
    supplier_name: str | None
    name: str
    external_warehouse_code: str | None
    fulfillment_modes: tuple[SupplierFulfillmentMode, ...]
    default_lead_time_seconds: int
    is_active: bool
    stock_update_policy: ListSupplierStockUpdatePolicyResponse

    @classmethod
    def from_dto(cls, dto: SupplierSourceListItemDTO) -> Self:
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
            stock_update_policy=ListSupplierStockUpdatePolicyResponse(
                ttl_seconds=dto.stock_ttl_seconds,
                stale_behavior=dto.stale_behavior,
                missing_sku_behavior=dto.missing_sku_behavior,
            ),
        )


from src.modules.supplier_sourcing.application.supplier_source.query.list_supplier_sources.dto import (
    ListSupplierSourcesResultDTO,
)


class ListSupplierSourcesResponse(BaseModel):
    """HTTP-страница справочника источников."""

    items: list[ListSupplierSourceItemResponse]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_dto(cls, dto: ListSupplierSourcesResultDTO) -> Self:
        """Преобразует страницу без потери фильтров и пагинации."""
        return cls(
            items=[ListSupplierSourceItemResponse.from_dto(item) for item in dto.items],
            total=dto.total,
            offset=dto.offset,
            limit=dto.limit,
        )
