from dataclasses import dataclass
from datetime import datetime
from typing import Self

from src.modules.inventory.domain.sku.error import (
    InvalidSkuCodeError,
    InvalidSkuTitleError,
)
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

    def __post_init__(self) -> None:
        if type(self.id) is not SkuIdVO:
            raise EntityIdTypeError("SKU identifier must use SkuIdVO.")
        if not isinstance(self.created_by, EntityIdVO) or not isinstance(
            self.updated_by, EntityIdVO
        ):
            raise EntityIdTypeError("SKU audit identifiers must use EntityIdVO.")
        if not isinstance(self.code, SkuCodeVO):
            raise InvalidSkuCodeError("SKU code must use SkuCodeVO.")
        if not isinstance(self.title, SkuTitleVO):
            raise InvalidSkuTitleError("SKU title must use SkuTitleVO.")

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
