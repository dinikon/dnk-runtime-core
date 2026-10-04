from dataclasses import dataclass
from datetime import datetime
from typing import Self

from src.modules.inventory.domain.sku.value_object.code import SkuCodeVO
from src.modules.inventory.domain.sku.value_object.identifier import SkuIdVO
from src.modules.inventory.domain.sku.value_object.title import SkuTitleVO
from src.modules.shared.domain.domain_error import EntityIdTypeError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class Sku:
    """Самостоятельная учётная единица Inventory со стабильным ID и аудитом."""

    id: SkuIdVO
    code: SkuCodeVO
    title: SkuTitleVO
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    @classmethod
    def create(
        cls,
        *,
        sku_id: SkuIdVO,
        code: str,
        title: str,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> Self:
        """Создаёт SKU с нормализованными значениями и единым аудитом."""
        return cls(
            id=sku_id,
            code=SkuCodeVO(code),
            title=SkuTitleVO(title),
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
        )
