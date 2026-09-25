from dataclasses import dataclass
from src.modules.contact_points.domain.label.error import InvalidContactPointLabelError


@dataclass(slots=True, frozen=True)
class ContactPointLabelNameVO:
    """Непустое нормализованное название подписи."""

    value: str

    def __post_init__(self):
        if not isinstance(self.value, str) or not 1 <= len(self.value.strip()) <= 100:
            raise InvalidContactPointLabelError(
                "Название должно содержать от 1 до 100 символов."
            )
        object.__setattr__(self, "value", self.value.strip())


__all__ = ["ContactPointLabelNameVO"]
