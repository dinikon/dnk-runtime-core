from collections.abc import Mapping
from typing import Any

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.warehousing.domain.warehouse.aggregate import Warehouse
from src.modules.warehousing.domain.warehouse.value_object.identifier import (
    WarehouseIdVO,
)
from src.modules.warehousing.domain.warehouse.value_object.policy import (
    WarehousePolicyVO,
)


class WarehouseMapper:
    """Преобразует storage-представление в агрегат и обратно без бизнес-проверок и I/O."""

    @staticmethod
    def to_insert_values(warehouse: Warehouse) -> dict[str, object]:
        """Извлекает значения проверенного агрегата для INSERT."""
        return {
            "id": warehouse.id.uuid,
            "code": warehouse.code.value,
            "title": warehouse.title.value,
            "type": warehouse.warehouse_type.value,
            "status": warehouse.status.value,
            "timezone": warehouse.policy.timezone,
            "revision": warehouse.revision,
            "created_at": warehouse.created_at,
            "updated_at": warehouse.updated_at,
            "created_by": warehouse.created_by.uuid,
            "updated_by": warehouse.updated_by.uuid,
        }

    @staticmethod
    def to_domain(row: Mapping[str, Any]) -> Warehouse:
        """Вызывает явную фабрику restore; инварианты остаются в Domain."""
        return Warehouse.restore(
            warehouse_id=WarehouseIdVO.from_value(row["id"]),
            code=row["code"],
            title=row["title"],
            warehouse_type=row["type"],
            status=row["status"],
            policy=WarehousePolicyVO(row["timezone"]),
            revision=row["revision"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=EntityIdVO.from_value(row["created_by"]),
            updated_by=EntityIdVO.from_value(row["updated_by"]),
        )
