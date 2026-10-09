from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.warehousing.domain.warehouse.error import (
    InvalidWarehouseStateError,
    InvalidWarehouseTimezoneError,
)
from src.modules.warehousing.domain.warehouse.value_object.code import WarehouseCodeVO
from src.modules.warehousing.domain.warehouse.value_object.identifier import (
    WarehouseIdVO,
)
from src.modules.warehousing.domain.warehouse.value_object.policy import (
    WarehousePolicyVO,
)
from src.modules.warehousing.domain.warehouse.value_object.status import WarehouseStatus
from src.modules.warehousing.domain.warehouse.value_object.title import WarehouseTitleVO
from src.modules.warehousing.domain.warehouse.value_object.warehouse_type import (
    WarehouseTypeVO,
)


@dataclass(slots=True)
class Warehouse:
    """Самостоятельный склад с политикой и аудитом, без зон, адресов и остатков."""

    id: WarehouseIdVO
    code: WarehouseCodeVO
    title: WarehouseTitleVO
    warehouse_type: WarehouseTypeVO
    status: WarehouseStatus
    policy: WarehousePolicyVO
    revision: int
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    @classmethod
    def create(
        cls,
        *,
        warehouse_id: WarehouseIdVO,
        code: str,
        title: str,
        warehouse_type: str,
        policy: WarehousePolicyVO,
        timezone_is_active: bool,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> Self:
        """Создаёт склад первой ревизии по переданному факту активности timezone."""
        warehouse = cls.restore(
            warehouse_id=warehouse_id,
            code=code,
            title=title,
            warehouse_type=warehouse_type,
            status=WarehouseStatus.ACTIVE.value,
            policy=policy,
            revision=1,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
            updated_by=actor_id,
        )
        if timezone_is_active is not True:
            raise InvalidWarehouseTimezoneError(
                "Часовой пояс отсутствует в активном справочнике."
            )
        return warehouse

    @classmethod
    def restore(
        cls,
        *,
        warehouse_id: WarehouseIdVO,
        code: str,
        title: str,
        warehouse_type: str,
        status: str,
        policy: WarehousePolicyVO,
        revision: int,
        created_at: datetime,
        updated_at: datetime,
        created_by: EntityIdVO,
        updated_by: EntityIdVO,
    ) -> Self:
        """Восстанавливает проверенное состояние без событий создания и изменения аудита."""
        if not isinstance(warehouse_id, WarehouseIdVO) or not all(
            isinstance(actor, EntityIdVO) for actor in (created_by, updated_by)
        ):
            raise InvalidWarehouseStateError(
                "Требуются типизированные идентификаторы склада и авторов."
            )
        if not isinstance(policy, WarehousePolicyVO):
            raise InvalidWarehouseStateError(
                "Требуется типизированная политика склада."
            )
        if type(revision) is not int or revision < 1:
            raise InvalidWarehouseStateError(
                "Ревизия склада должна быть положительным целым."
            )
        try:
            restored_status = WarehouseStatus(status)
        except (ValueError, TypeError) as exc:
            raise InvalidWarehouseStateError("Неизвестный статус склада.") from exc
        created = cls._utc(created_at)
        updated = cls._utc(updated_at)
        if updated < created:
            raise InvalidWarehouseStateError(
                "Изменение не может предшествовать созданию склада."
            )
        return cls(
            id=warehouse_id,
            code=WarehouseCodeVO(code),
            title=WarehouseTitleVO(title),
            warehouse_type=WarehouseTypeVO(warehouse_type),
            status=restored_status,
            policy=policy,
            revision=revision,
            created_at=created,
            updated_at=updated,
            created_by=created_by,
            updated_by=updated_by,
        )

    @staticmethod
    def _utc(value: datetime) -> datetime:
        """Отклоняет naive datetime и приводит время аудита к UTC."""
        if not isinstance(value, datetime) or value.utcoffset() is None:
            raise InvalidWarehouseStateError(
                "Время аудита должно содержать часовой пояс."
            )
        return value.astimezone(UTC)
