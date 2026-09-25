from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from src.modules.contact_points.infrastructure.persistence.base import (
    ContactPointPersistenceMappingError,
)
from src.modules.shared.domain.domain_error import DomainError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.contact_points.domain.binding.entity import ContactPointBinding
from src.modules.contact_points.domain.binding.repository import BoundContactPoint
from src.modules.contact_points.domain.binding.value_object.identifier import (
    ContactPointBindingIdVO,
)
from src.modules.contact_points.domain.binding.value_object.target import (
    ContactPointTargetVO,
)
from src.modules.contact_points.domain.contact_point.value_object.identifier import (
    ContactPointIdVO,
)
from src.modules.contact_points.domain.label.value_object.identifier import (
    ContactPointLabelIdVO,
)
from src.modules.contact_points.infrastructure.persistence.mappers.contact_point_mapper import (
    ContactPointMapper,
)


class ContactPointBindingMapper:
    """Явное преобразование ContactPointBinding между persistence и domain."""

    @staticmethod
    def to_domain(row: Mapping[str, Any]) -> ContactPointBinding:
        """Проверяет сохранённые поля и восстанавливает domain entity."""
        try:
            if (
                not isinstance(row["id"], (UUID, str))
                or not isinstance(row["contact_point_id"], (UUID, str))
                or not isinstance(row["created_by"], (UUID, str))
                or not isinstance(row["updated_by"], (UUID, str))
                or (
                    row["label_id"] is not None
                    and not isinstance(row["label_id"], (UUID, str))
                )
                or type(row["position"]) is not int
            ):
                raise TypeError("Invalid persisted ContactPointBinding field types.")
            if (
                not isinstance(row["created_at"], datetime)
                or row["created_at"].utcoffset() is None
                or not isinstance(row["updated_at"], datetime)
                or row["updated_at"].utcoffset() is None
            ):
                raise TypeError(
                    "Persisted timestamps must be timezone-aware datetimes."
                )
            return ContactPointBinding(
                id=ContactPointBindingIdVO.from_value(row["id"]),
                contact_point_id=ContactPointIdVO.from_value(row["contact_point_id"]),
                target=ContactPointBindingMapper.to_target(row),
                label_id=(
                    ContactPointLabelIdVO.from_value(row["label_id"])
                    if row["label_id"] is not None
                    else None
                ),
                position=row["position"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                created_by=EntityIdVO.from_value(row["created_by"]),
                updated_by=EntityIdVO.from_value(row["updated_by"]),
            )
        except (KeyError, TypeError, ValueError, DomainError) as exc:
            raise ContactPointPersistenceMappingError(
                "Invalid persisted ContactPointBinding."
            ) from exc

    @staticmethod
    def to_insert_values(entity: ContactPointBinding) -> dict[str, Any]:
        """Перечисляет INSERT values без создания ORM instance."""
        return {
            "id": entity.id.uuid,
            "contact_point_id": entity.contact_point_id.uuid,
            "model_key": entity.target.model_key,
            "record_id": entity.target.record_id.uuid,
            "label_id": entity.label_id.uuid if entity.label_id is not None else None,
            "position": entity.position,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "created_by": entity.created_by.uuid,
            "updated_by": entity.updated_by.uuid,
        }

    @staticmethod
    def to_target(row: Mapping[str, Any]) -> ContactPointTargetVO:
        """Преобразует проекцию владельца для reverse lookup."""
        try:
            if not isinstance(row["model_key"], str) or not isinstance(
                row["record_id"], (UUID, str)
            ):
                raise TypeError("Invalid persisted target fields.")
            return ContactPointTargetVO(
                model_key=row["model_key"],
                record_id=EntityIdVO.from_value(row["record_id"]),
            )
        except (KeyError, TypeError, ValueError, DomainError) as exc:
            raise ContactPointPersistenceMappingError(
                "Invalid persisted contact point target."
            ) from exc

    @staticmethod
    def to_bound_domain(row: Mapping[str, Any]) -> BoundContactPoint:
        """Разделяет фиксированные aliases JOIN между двумя мапперами."""
        try:
            return BoundContactPoint(
                binding=ContactPointBindingMapper.to_domain(row),
                point=ContactPointMapper.to_domain(
                    {
                        "id": row["point_id"],
                        "type": row["point_type"],
                        "canonical_value": row["point_canonical_value"],
                        "country_code": row["point_country_code"],
                        "created_at": row["point_created_at"],
                        "updated_at": row["point_updated_at"],
                        "created_by": row["point_created_by"],
                        "updated_by": row["point_updated_by"],
                    }
                ),
            )
        except KeyError as exc:
            raise ContactPointPersistenceMappingError(
                "Incomplete persisted binding/point projection."
            ) from exc


__all__ = ["ContactPointBindingMapper"]
