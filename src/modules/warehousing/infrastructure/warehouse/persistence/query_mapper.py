from collections.abc import Mapping
from datetime import UTC
from typing import Any

from src.modules.warehousing.application.warehouse.query.get_warehouse.dto import (
    GetWarehouseDetailsDTO,
    GetWarehousePolicyDTO,
)
from src.modules.warehousing.application.warehouse.query.list_warehouses.dto import (
    ListWarehouseItemDTO,
)


class WarehouseQueryMapper:
    """Преобразует SQL-проекции в DTO конкретных сценариев без Domain restore."""

    @staticmethod
    def to_details(row: Mapping[str, Any]) -> GetWarehouseDetailsDTO:
        """Возвращает полную проекцию карточки с её собственным DTO policy."""
        return GetWarehouseDetailsDTO(
            id=row["id"],
            code=row["code"],
            title=row["title"],
            type=row["type"],
            status=row["status"],
            policy=GetWarehousePolicyDTO(timezone=row["timezone"]),
            revision=row["revision"],
            created_at=row["created_at"].astimezone(UTC),
            updated_at=row["updated_at"].astimezone(UTC),
            created_by=row["created_by"],
            updated_by=row["updated_by"],
        )

    @staticmethod
    def to_list_item(row: Mapping[str, Any]) -> ListWarehouseItemDTO:
        """Создаёт DTO строки списка без использования контракта карточки."""
        return ListWarehouseItemDTO(
            id=row["id"],
            code=row["code"],
            title=row["title"],
            type=row["type"],
            status=row["status"],
            revision=row["revision"],
        )
