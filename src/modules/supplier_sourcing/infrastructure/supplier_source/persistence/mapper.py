from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierReferenceVO,
)
from collections.abc import Sequence
from datetime import timedelta
from typing import Any
from src.modules.supplier_sourcing.domain.supplier_source.aggregate import (
    SupplierSource,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.identifier import (
    SupplierSourceIdVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.name import (
    SupplierSourceNameVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.external_warehouse_code import (
    ExternalWarehouseCodeVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.fulfillment_mode import (
    SupplierFulfillmentMode,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.stock_update_policy import (
    SupplierStockUpdatePolicyVO,
    StaleStockBehavior,
    MissingSkuBehavior,
)
from src.modules.supplier_sourcing.domain.value_object.lead_time import (
    SupplierLeadTimeVO,
)
from src.modules.supplier_sourcing.infrastructure.persistence.models.supplier_source import (
    SupplierSourceModel,
)
from src.modules.supplier_sourcing.infrastructure.persistence.models.supplier_source_fulfillment_mode import (
    SupplierSourceFulfillmentModeModel,
)


class SupplierSourceMapper:
    """Преобразует сохранённую карточку и набор режимов без SQL."""

    @staticmethod
    def to_domain(
        model: SupplierSourceModel, modes: Sequence[SupplierSourceFulfillmentModeModel]
    ) -> SupplierSource:
        """Восстанавливает источник через Domain с прежней идентичностью."""
        return SupplierSource.restore(
            identifier=SupplierSourceIdVO.from_value(model.id),
            supplier=SupplierReferenceVO.from_value(
                model.supplier_model_key, model.supplier_id
            ),
            name=SupplierSourceNameVO(model.name),
            external_warehouse_code=(
                ExternalWarehouseCodeVO(model.external_warehouse_code)
                if model.external_warehouse_code is not None
                else None
            ),
            fulfillment_modes=frozenset(
                SupplierFulfillmentMode(mode.mode) for mode in modes
            ),
            default_lead_time=SupplierLeadTimeVO(
                timedelta(seconds=model.default_lead_time_seconds)
            ),
            is_active=model.is_active,
            stock_update_policy=SupplierStockUpdatePolicyVO(
                timedelta(seconds=model.stock_ttl_seconds),
                StaleStockBehavior(model.stale_behavior),
                MissingSkuBehavior(model.missing_sku_behavior),
            ),
        )

    @staticmethod
    def to_update_values(source: SupplierSource) -> dict[str, Any]:
        """Извлекает изменяемые поля; supplier_id остаётся неизменным."""
        return dict(
            name=source.name.value,
            external_warehouse_code=(
                source.external_warehouse_code.value
                if source.external_warehouse_code is not None
                else None
            ),
            default_lead_time_seconds=SupplierSourceMapper._seconds(
                source.default_lead_time.value
            ),
            stock_ttl_seconds=SupplierSourceMapper._seconds(
                source.stock_update_policy.ttl
            ),
            stale_behavior=source.stock_update_policy.stale_behavior.value,
            missing_sku_behavior=source.stock_update_policy.missing_sku_behavior.value,
            is_active=source.is_active,
        )

    @staticmethod
    def to_insert_values(source: SupplierSource) -> dict[str, Any]:
        """Добавляет идентификаторы при первой записи."""
        return dict(
            id=source.id.uuid,
            supplier_model_key=source.supplier.model_key.value,
            supplier_id=source.supplier.identifier.uuid,
            **SupplierSourceMapper.to_update_values(source),
        )

    @staticmethod
    def to_mode_insert_values(source: SupplierSource) -> list[dict[str, Any]]:
        """Сохраняет значения набора в стабильном порядке."""
        return [
            dict(supplier_source_id=source.id.uuid, mode=mode.value)
            for mode in sorted(source.fulfillment_modes)
        ]

    @staticmethod
    def _seconds(value: timedelta) -> int:
        """Отклоняет неподдерживаемую точность хранения вместо скрытого округления."""
        if value.microseconds:
            raise ValueError("Хранение SupplierSource поддерживает целые секунды.")
        return value // timedelta(seconds=1)
