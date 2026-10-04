from dataclasses import dataclass
from datetime import datetime
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
)
from src.modules.contact_points.domain.label.value_object.identifier import (
    ContactPointLabelIdVO,
)
from src.modules.contact_points.domain.label.value_object.name import (
    ContactPointLabelNameVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True)
class ContactPointLabel:
    """Настраиваемая подпись одного вида контактных точек."""

    id: ContactPointLabelIdVO
    type: ContactPointType
    name: ContactPointLabelNameVO
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO | None
    updated_by: EntityIdVO | None

    @classmethod
    def create(cls, *, label_id, point_type, name, actor_id, now):
        """Создаёт активную подпись пользователя."""
        return cls(
            label_id,
            point_type,
            ContactPointLabelNameVO(name),
            True,
            now,
            now,
            actor_id,
            actor_id,
        )

    def update(self, *, name, is_active, actor_id, now):
        """Переименовывает или архивирует подпись без удаления связей."""
        next_name = self.name if name is None else ContactPointLabelNameVO(name)
        active = self.is_active if is_active is None else is_active
        if (self.name, self.is_active) == (next_name, active):
            return False
        self.name, self.is_active = next_name, active
        self.updated_at, self.updated_by = now, actor_id
        return True


__all__ = ["ContactPointLabel"]
