"""Публичные VO и ошибки, используемые контрактами интеграции."""

from src.modules.contact_points.domain.binding.value_object.identifier import (
    ContactPointBindingIdVO,
)
from src.modules.contact_points.domain.binding.value_object.target import (
    ContactPointTargetVO,
)
from src.modules.contact_points.domain.binding.value_object.draft import (
    ContactPointDraftVO,
)
from src.modules.contact_points.domain.binding.error import (
    InvalidContactPointBindingError,
)
from src.modules.contact_points.domain.contact_point.value_object.identifier import (
    ContactPointIdVO,
)
from src.modules.contact_points.domain.label.value_object.identifier import (
    ContactPointLabelIdVO,
)

__all__ = [
    "ContactPointBindingIdVO",
    "ContactPointTargetVO",
    "ContactPointDraftVO",
    "InvalidContactPointBindingError",
    "ContactPointIdVO",
    "ContactPointLabelIdVO",
]
