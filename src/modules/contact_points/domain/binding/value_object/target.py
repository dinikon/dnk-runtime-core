from dataclasses import dataclass
import re
from src.modules.contact_points.domain.binding.error import (
    InvalidContactPointTargetError,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class ContactPointTargetVO:
    """Стабильный ключ модели и идентификатор её записи."""

    model_key: str
    record_id: EntityIdVO

    def __post_init__(self):
        if (
            not isinstance(self.model_key, str)
            or len(self.model_key) > 100
            or not re.fullmatch(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*", self.model_key)
        ):
            raise InvalidContactPointTargetError("Некорректный ключ модели.")
        if type(self.record_id) is not EntityIdVO:
            raise InvalidContactPointTargetError("Target требует EntityIdVO.")


__all__ = ["ContactPointTargetVO"]
