from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from src.modules.contact_points.infrastructure.persistence.base import (
    ContactPointPersistenceMappingError,
)
from src.modules.shared.domain.domain_error import DomainError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.contact_points.domain.contact_point.entity import ContactPoint
from src.modules.contact_points.domain.contact_point.value_object.identifier import (
    ContactPointIdVO,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
    ContactPointValueVO,
)


class ContactPointMapper:
    """Явное преобразование ContactPoint между persistence и domain."""

    @staticmethod
    def to_domain(row: Mapping[str, Any]) -> ContactPoint:
        """Проверяет сохранённые поля и восстанавливает domain entity."""
        try:
            if (
                not isinstance(row["id"], (UUID, str))
                or not isinstance(row["created_by"], (UUID, str))
                or not isinstance(row["updated_by"], (UUID, str))
                or not isinstance(row["type"], str)
                or not isinstance(row["canonical_value"], str)
                or (
                    row["country_code"] is not None
                    and not isinstance(row["country_code"], str)
                )
            ):
                raise TypeError("Invalid persisted ContactPoint field types.")
            if (
                not isinstance(row["created_at"], datetime)
                or row["created_at"].utcoffset() is None
                or not isinstance(row["updated_at"], datetime)
                or row["updated_at"].utcoffset() is None
            ):
                raise TypeError(
                    "Persisted timestamps must be timezone-aware datetimes."
                )
            return ContactPoint(
                id=ContactPointIdVO.from_value(row["id"]),
                type=ContactPointType(row["type"]),
                canonical_value=ContactPointValueVO(row["canonical_value"]),
                country_code=row["country_code"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                created_by=EntityIdVO.from_value(row["created_by"]),
                updated_by=EntityIdVO.from_value(row["updated_by"]),
            )
        except (KeyError, TypeError, ValueError, DomainError) as exc:
            raise ContactPointPersistenceMappingError(
                "Invalid persisted ContactPoint."
            ) from exc

    @staticmethod
    def to_insert_values(entity: ContactPoint) -> dict[str, Any]:
        """Перечисляет INSERT values без создания ORM instance."""
        return {
            "id": entity.id.uuid,
            "type": entity.type.value,
            "canonical_value": entity.canonical_value.value,
            "country_code": entity.country_code,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "created_by": entity.created_by.uuid,
            "updated_by": entity.updated_by.uuid,
        }


__all__ = ["ContactPointMapper"]
