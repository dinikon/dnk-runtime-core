from dataclasses import dataclass

from src.modules.supplier_sourcing.domain.supplier_source.error import (
    InvalidSupplierSourceValueError,
)
from src.modules.supplier_sourcing.domain.supplier_source.identity_snapshot import (
    SupplierSourceIdentitySnapshot,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.stock_update_policy import (
    SupplierStockUpdatePolicyVO,
)


@dataclass(frozen=True, slots=True)
class SupplierSourceAvailabilitySnapshot:
    """Передаёт идентичность источника и его настройки актуальности."""

    identity: SupplierSourceIdentitySnapshot
    stock_update_policy: SupplierStockUpdatePolicyVO

    def ensure_valid(self) -> None:
        """Проверяет идентичность и наличие типизированной политики обновления."""
        if not isinstance(
            self.identity, SupplierSourceIdentitySnapshot
        ) or not isinstance(self.stock_update_policy, SupplierStockUpdatePolicyVO):
            raise InvalidSupplierSourceValueError(
                "Нужны идентичность источника и политика обновления наличия."
            )
        self.identity.ensure_valid()
