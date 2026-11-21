from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from src.modules.supplier_sourcing.domain.supplier_source.error import (
    InvalidSupplierStockUpdatePolicyError,
)


class StaleStockBehavior(StrEnum):
    """Настраивает интерпретацию устаревшего внешнего наличия."""

    MARK_UNKNOWN = "MARK_UNKNOWN"
    BLOCK_AUTOMATIC_SALE = "BLOCK_AUTOMATIC_SALE"


class MissingSkuBehavior(StrEnum):
    """Настраивает обработку SKU, отсутствующего в успешном полном снимке."""

    KEEP_LAST = "KEEP_LAST"
    MARK_UNKNOWN = "MARK_UNKNOWN"


@dataclass(frozen=True, slots=True)
class SupplierStockUpdatePolicyVO:
    """Хранит время актуальности и правила интерпретации данных источника."""

    ttl: timedelta
    stale_behavior: StaleStockBehavior
    missing_sku_behavior: MissingSkuBehavior

    def __post_init__(self) -> None:
        """Требует положительный TTL и явные значения обеих политик."""
        if (
            not isinstance(self.ttl, timedelta)
            or self.ttl <= timedelta(0)
            or not isinstance(self.stale_behavior, StaleStockBehavior)
            or not isinstance(self.missing_sku_behavior, MissingSkuBehavior)
        ):
            raise InvalidSupplierStockUpdatePolicyError(
                "Нужны положительный TTL и типизированные правила устаревания и отсутствия SKU."
            )
