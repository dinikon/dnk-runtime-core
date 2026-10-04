from dataclasses import dataclass
from src.modules.contact_points.domain.label.value_object.identifier import (
    ContactPointLabelIdVO,
)
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
)


@dataclass(slots=True, frozen=True)
class CreateContactPointLabelDTO:
    """Подпись для выбора или административных настроек."""

    id: ContactPointLabelIdVO
    type: ContactPointType
    name: str
    is_active: bool


def label_dto(label):
    """Мапит сущность настройки в публичные поля."""
    return CreateContactPointLabelDTO(
        label.id, label.type, label.name.value, label.is_active
    )


__all__ = ["CreateContactPointLabelDTO", "label_dto"]
