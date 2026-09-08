from dataclasses import dataclass
from datetime import datetime

from src.modules.inventory.domain.warehouse.error import (
    InvalidWarehouseTitleError,
    WarehouseSelfParentError,
)
from src.modules.inventory.domain.warehouse.value_object import WarehouseIdVO
from src.modules.shared.domain.domain_error import EntityIdTypeError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.entity_title import EntityTitleVO


@dataclass(slots=True)
class Warehouse:
    """Склад с необязательной ссылкой на родительский склад."""

    id: WarehouseIdVO
    title: EntityTitleVO
    parent_id: WarehouseIdVO | None
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    def __post_init__(self) -> None:
        if type(self.id) is not WarehouseIdVO or (
            self.parent_id is not None and type(self.parent_id) is not WarehouseIdVO
        ):
            raise EntityIdTypeError("Warehouse identifiers must use WarehouseIdVO.")
        if not isinstance(self.created_by, EntityIdVO) or not isinstance(
            self.updated_by, EntityIdVO
        ):
            raise EntityIdTypeError("Warehouse audit identifiers must use EntityIdVO.")
        if not isinstance(self.title, EntityTitleVO) or not self.title.value.strip():
            raise InvalidWarehouseTitleError("Warehouse title must not be empty.")
        self.title = EntityTitleVO(self.title.value.strip())
        if self.parent_id == self.id:
            raise WarehouseSelfParentError("Warehouse cannot be its own parent.")

    @classmethod
    def create(
        cls,
        *,
        warehouse_id: WarehouseIdVO,
        title: str,
        actor_id: EntityIdVO,
        now: datetime,
        parent_id: WarehouseIdVO | None = None,
    ) -> "Warehouse":
        """Создаёт склад с едиными значениями времени и авторства."""
        if not isinstance(title, str):
            raise InvalidWarehouseTitleError("Warehouse title must be a string.")
        try:
            title_vo = EntityTitleVO(title.strip())
        except ValueError as exc:
            raise InvalidWarehouseTitleError(str(exc)) from exc
        return cls(
            id=warehouse_id,
            title=title_vo,
            parent_id=parent_id,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
        )
