from dataclasses import dataclass
from datetime import timedelta
from src.modules.supplier_sourcing.domain.supplier_source.value_object.stock_update_policy import (
    SupplierStockUpdatePolicyVO,
    StaleStockBehavior,
    MissingSkuBehavior,
)


@dataclass(frozen=True, slots=True)
class SupplierStockUpdatePolicyInput:
    """Передаёт цельную настройку актуальности в сценарии записи."""

    ttl_seconds: int
    stale_behavior: StaleStockBehavior
    missing_sku_behavior: MissingSkuBehavior

    def to_value_object(self) -> SupplierStockUpdatePolicyVO:
        """Преобразует единицу транспорта в проверяемое Domain значение."""
        return SupplierStockUpdatePolicyVO(
            timedelta(seconds=self.ttl_seconds),
            self.stale_behavior,
            self.missing_sku_behavior,
        )
