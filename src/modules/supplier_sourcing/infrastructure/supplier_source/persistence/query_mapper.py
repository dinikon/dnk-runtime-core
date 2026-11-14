from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierModelKey,
)
from collections.abc import Sequence
from src.modules.supplier_sourcing.infrastructure.persistence.models.supplier_source import (
    SupplierSourceModel,
)
from src.modules.supplier_sourcing.infrastructure.persistence.models.supplier_source_fulfillment_mode import (
    SupplierSourceFulfillmentModeModel,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.fulfillment_mode import (
    SupplierFulfillmentMode,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.stock_update_policy import (
    StaleStockBehavior,
    MissingSkuBehavior,
)
from src.modules.supplier_sourcing.application.supplier_source.query.get_supplier_source.dto import (
    GetSupplierSourceResultDTO,
)
from src.modules.supplier_sourcing.application.supplier_source.query.list_supplier_sources.dto import (
    SupplierSourceListItemDTO,
)


class SupplierSourceQueryMapper:
    """Собирает типизированные проекции без восстановления Domain."""

    @staticmethod
    def to_details(
        model: SupplierSourceModel, modes: Sequence[SupplierSourceFulfillmentModeModel]
    ) -> GetSupplierSourceResultDTO:
        """Преобразует карточку в результат сценария чтения."""
        return GetSupplierSourceResultDTO(
            id=model.id,
            supplier_model_key=SupplierModelKey(model.supplier_model_key),
            supplier_id=model.supplier_id,
            name=model.name,
            external_warehouse_code=model.external_warehouse_code,
            fulfillment_modes=tuple(
                SupplierFulfillmentMode(mode.mode) for mode in modes
            ),
            default_lead_time_seconds=model.default_lead_time_seconds,
            is_active=model.is_active,
            stock_ttl_seconds=model.stock_ttl_seconds,
            stale_behavior=StaleStockBehavior(model.stale_behavior),
            missing_sku_behavior=MissingSkuBehavior(model.missing_sku_behavior),
        )

    @staticmethod
    def to_list_item(
        model: SupplierSourceModel, modes: Sequence[SupplierSourceFulfillmentModeModel]
    ) -> SupplierSourceListItemDTO:
        """Преобразует одну строку страницы справочника."""
        return SupplierSourceListItemDTO(
            id=model.id,
            supplier_model_key=SupplierModelKey(model.supplier_model_key),
            supplier_id=model.supplier_id,
            name=model.name,
            external_warehouse_code=model.external_warehouse_code,
            fulfillment_modes=tuple(
                SupplierFulfillmentMode(mode.mode) for mode in modes
            ),
            default_lead_time_seconds=model.default_lead_time_seconds,
            is_active=model.is_active,
            stock_ttl_seconds=model.stock_ttl_seconds,
            stale_behavior=StaleStockBehavior(model.stale_behavior),
            missing_sku_behavior=MissingSkuBehavior(model.missing_sku_behavior),
        )
