from dataclasses import dataclass
from datetime import datetime
from src.modules.shared.domain.domain_error import DomainError, EntityIdTypeError
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
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True)
class ContactPointBinding:
    """Связь объекта с точкой; смена адреса сохраняет binding id."""

    id: ContactPointBindingIdVO
    contact_point_id: ContactPointIdVO
    target: ContactPointTargetVO
    label_id: ContactPointLabelIdVO | None
    position: int
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    def __post_init__(self):
        if (
            type(self.id) is not ContactPointBindingIdVO
            or type(self.contact_point_id) is not ContactPointIdVO
        ):
            raise EntityIdTypeError("Binding identifiers require their specific VO.")
        if not isinstance(self.target, ContactPointTargetVO):
            raise DomainError("Binding target must use ContactPointTargetVO.")
        if (
            self.label_id is not None
            and type(self.label_id) is not ContactPointLabelIdVO
        ):
            raise EntityIdTypeError("Label identifier must use ContactPointLabelIdVO.")
        if type(self.position) is not int or self.position < 0:
            raise DomainError("Binding position must be a non-negative integer.")

    @classmethod
    def create(cls, *, binding_id, point_id, target, label_id, position, actor_id, now):
        """Создаёт связь с исходным audit."""
        return cls(
            binding_id,
            point_id,
            target,
            label_id,
            position,
            now,
            now,
            actor_id,
            actor_id,
        )

    def update(self, *, point_id, label_id, position, actor_id, now):
        """Меняет только фактически изменённые поля связи."""
        if type(point_id) is not ContactPointIdVO or (
            label_id is not None and type(label_id) is not ContactPointLabelIdVO
        ):
            raise EntityIdTypeError(
                "Binding update requires typed point and label identifiers."
            )
        if type(position) is not int or position < 0:
            raise DomainError("Binding position must be a non-negative integer.")
        if (self.contact_point_id, self.label_id, self.position) == (
            point_id,
            label_id,
            position,
        ):
            return False
        self.contact_point_id, self.label_id, self.position = (
            point_id,
            label_id,
            position,
        )
        self.updated_at, self.updated_by = now, actor_id
        return True


__all__ = ["ContactPointBinding"]
