from dataclasses import dataclass
from src.modules.contact_points.domain.value_object.binding_identifier import (
    ContactPointBindingIdVO,
)
from src.modules.contact_points.domain.value_object.contact_point_identifier import (
    ContactPointIdVO,
)
from src.modules.contact_points.domain.value_object.label_identifier import (
    ContactPointLabelIdVO,
)


@dataclass(slots=True, frozen=True)
class ContactPointDraftVO:
    """Запрошенная строка с подготовленными на boundary идентификаторами."""

    candidate_point_id: ContactPointIdVO
    candidate_binding_id: ContactPointBindingIdVO
    value: str
    binding_id: ContactPointBindingIdVO | None = None
    label_id: ContactPointLabelIdVO | None = None
    country_code: str | None = None


__all__ = ["ContactPointDraftVO"]
