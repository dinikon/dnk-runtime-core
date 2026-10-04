from dataclasses import dataclass
from src.modules.contact_points.domain.binding.value_object.identifier import (
    ContactPointBindingIdVO,
)
from src.modules.contact_points.domain.binding.value_object.target import (
    ContactPointTargetVO,
)
from src.modules.contact_points.domain.contact_point.value_object.identifier import (
    ContactPointIdVO,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
)
from src.modules.contact_points.domain.label.value_object.identifier import (
    ContactPointLabelIdVO,
)


@dataclass(slots=True, frozen=True)
class ContactPointBindingDTO:
    """Публичные данные связи, без ORM и владельца CRM."""

    target: ContactPointTargetVO
    binding_id: ContactPointBindingIdVO
    contact_point_id: ContactPointIdVO
    type: ContactPointType
    value: str
    country_code: str | None
    label_id: ContactPointLabelIdVO | None
    position: int


def binding_dto(row):
    """Преобразует domain-проекцию в DTO."""
    b, p = row.binding, row.point
    return ContactPointBindingDTO(
        b.target,
        b.id,
        p.id,
        p.type,
        p.canonical_value.value,
        p.country_code,
        b.label_id,
        b.position,
    )


__all__ = ["ContactPointBindingDTO", "binding_dto"]
