from dataclasses import dataclass
from datetime import datetime
from src.modules.contact_points.domain.contact_point.value_object.identifier import (
    ContactPointIdVO,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
    ContactPointValueVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.domain_error import EntityIdTypeError
from src.modules.contact_points.domain.contact_point.error import (
    InvalidContactPointError,
)


@dataclass(slots=True, frozen=True)
class ContactPoint:
    """Неизменяемый канонический адрес, общий для объектов tenant."""

    id: ContactPointIdVO
    type: ContactPointType
    canonical_value: ContactPointValueVO
    country_code: str | None
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    def __post_init__(self) -> None:
        if type(self.id) is not ContactPointIdVO:
            raise EntityIdTypeError("Point identifier must use ContactPointIdVO.")
        if not isinstance(self.type, ContactPointType) or not isinstance(
            self.canonical_value, ContactPointValueVO
        ):
            raise InvalidContactPointError(
                "Point type and value must use domain types."
            )
        if self.type == ContactPointType.PHONE:
            if (
                not isinstance(self.country_code, str)
                or len(self.country_code) != 2
                or not self.country_code.isupper()
            ):
                raise InvalidContactPointError(
                    "Phone country must be an uppercase region code.", "country_code"
                )
        elif self.country_code is not None:
            raise InvalidContactPointError(
                "Email must not have a phone country.", "country_code"
            )

    @classmethod
    def create(cls, *, point_id, point_type, normalized, actor_id, now):
        """Создаёт нормализованную точку с единым audit."""
        return cls(
            point_id,
            point_type,
            normalized.value,
            normalized.country_code,
            now,
            now,
            actor_id,
            actor_id,
        )


__all__ = ["ContactPoint"]
