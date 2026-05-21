from dataclasses import dataclass

from src.modules.contact_point.domain.binding.value_object import (
    ContactPointBindingIdVO,
)
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class DetachContactPointCommand:
    tenant_id: EntityIdVO
    binding_id: ContactPointBindingIdVO


__all__ = ["DetachContactPointCommand"]
