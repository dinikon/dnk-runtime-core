from dataclasses import dataclass, replace
from datetime import datetime
from typing import Self

from src.modules.inventory.domain.warehouse.error import WarehouseSelfParentError
from src.modules.inventory.domain.warehouse.value_object.title import WarehouseTitleVO
from src.modules.inventory.domain.warehouse.value_object.warehouse_id import (
    WarehouseIdVO,
)
from src.modules.shared.domain.domain_error import EntityIdTypeError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class Warehouse:
    """Корень агрегата склада с управляемыми названием и родительской ссылкой."""

    id: WarehouseIdVO
    title: WarehouseTitleVO
    parent_id: WarehouseIdVO | None
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    @classmethod
    def create(
        cls,
        *,
        warehouse_id: WarehouseIdVO,
        title: str,
        actor_id: EntityIdVO,
        now: datetime,
        parent_id: WarehouseIdVO | None = None,
    ) -> Self:
        """Создаёт склад после проверки идентификаторов и названия."""
        cls._validate_identity(warehouse_id, parent_id)
        cls._validate_actor(actor_id)
        return cls(
            id=warehouse_id,
            title=WarehouseTitleVO(title),
            parent_id=parent_id,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
        )

    def rename(self, *, title: str, actor_id: EntityIdVO, now: datetime) -> Self:
        """Возвращает переименованный склад; одинаковое название не меняет аудит."""
        self._validate_actor(actor_id)
        next_title = WarehouseTitleVO(title)
        if next_title == self.title:
            return self
        return replace(self, title=next_title, updated_at=now, updated_by=actor_id)

    def change_parent(
        self,
        *,
        parent_id: WarehouseIdVO | None,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> Self:
        """Возвращает склад с новым родителем, запрещая ссылку на самого себя."""
        self._validate_actor(actor_id)
        self._validate_identity(self.id, parent_id)
        if parent_id == self.parent_id:
            return self
        return replace(self, parent_id=parent_id, updated_at=now, updated_by=actor_id)

    @staticmethod
    def _validate_identity(
        warehouse_id: WarehouseIdVO, parent_id: WarehouseIdVO | None
    ) -> None:
        if type(warehouse_id) is not WarehouseIdVO or (
            parent_id is not None and type(parent_id) is not WarehouseIdVO
        ):
            raise EntityIdTypeError("Warehouse identifiers must use WarehouseIdVO.")
        if parent_id == warehouse_id:
            raise WarehouseSelfParentError("Warehouse cannot be its own parent.")

    @staticmethod
    def _validate_actor(actor_id: EntityIdVO) -> None:
        if not isinstance(actor_id, EntityIdVO):
            raise EntityIdTypeError("Warehouse audit identifiers must use EntityIdVO.")
