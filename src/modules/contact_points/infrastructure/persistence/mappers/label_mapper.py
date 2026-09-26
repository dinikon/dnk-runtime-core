from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from src.modules.contact_points.infrastructure.persistence.base import (
    ContactPointPersistenceMappingError,
)
from src.modules.shared.domain.domain_error import DomainError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.contact_points.domain.label.entity import ContactPointLabel
from src.modules.contact_points.domain.label.value_object.identifier import (
    ContactPointLabelIdVO,
)
from src.modules.contact_points.domain.label.value_object.name import (
    ContactPointLabelNameVO,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
)


class ContactPointLabelMapper:
    """Явное преобразование ContactPointLabel между persistence и domain."""

    @staticmethod
    def to_domain(row: Mapping[str, Any]) -> ContactPointLabel:
        """Проверяет сохранённые поля и восстанавливает domain entity."""
        try:
            if (
                not isinstance(row["id"], (UUID, str))
                or (
                    row["created_by"] is not None
                    and not isinstance(row["created_by"], (UUID, str))
                )
                or (
                    row["updated_by"] is not None
                    and not isinstance(row["updated_by"], (UUID, str))
                )
                or not isinstance(row["type"], str)
                or not isinstance(row["name"], str)
                or type(row["is_active"]) is not bool
            ):
                raise TypeError("Invalid persisted ContactPointLabel field types.")
            if (
                not isinstance(row["created_at"], datetime)
                or row["created_at"].utcoffset() is None
                or not isinstance(row["updated_at"], datetime)
                or row["updated_at"].utcoffset() is None
            ):
                raise TypeError(
                    "Persisted timestamps must be timezone-aware datetimes."
                )
            return ContactPointLabel(
                id=ContactPointLabelIdVO.from_value(row["id"]),
                type=ContactPointType(row["type"]),
                name=ContactPointLabelNameVO(row["name"]),
                is_active=row["is_active"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                created_by=(
                    EntityIdVO.from_value(row["created_by"])
                    if row["created_by"] is not None
                    else None
                ),
                updated_by=(
                    EntityIdVO.from_value(row["updated_by"])
                    if row["updated_by"] is not None
                    else None
                ),
            )
        except (KeyError, TypeError, ValueError, DomainError) as exc:
            raise ContactPointPersistenceMappingError(
                "Invalid persisted ContactPointLabel."
            ) from exc

    @staticmethod
    def to_insert_values(entity: ContactPointLabel) -> dict[str, Any]:
        """Перечисляет INSERT values без создания ORM instance."""
        return {
            "id": entity.id.uuid,
            "type": entity.type.value,
            "name": entity.name.value,
            "is_active": entity.is_active,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "created_by": (
                entity.created_by.uuid if entity.created_by is not None else None
            ),
            "updated_by": (
                entity.updated_by.uuid if entity.updated_by is not None else None
            ),
        }

    @staticmethod
    def to_update_values(entity: ContactPointLabel) -> dict[str, Any]:
        """Оставляет id, type и create audit неизменными."""
        return {
            "name": entity.name.value,
            "is_active": entity.is_active,
            "updated_at": entity.updated_at,
            "updated_by": (
                entity.updated_by.uuid if entity.updated_by is not None else None
            ),
        }


__all__ = ["ContactPointLabelMapper"]
