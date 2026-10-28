import re
from dataclasses import dataclass
from src.modules.funnel.domain.error import FunnelError


@dataclass(frozen=True, slots=True)
class StageColorVO:
    """Непрозрачный RGB-цвет стадии в каноническом HEX-формате."""

    value: str

    def __post_init__(self) -> None:
        """Проверяет шесть HEX-символов и нормализует регистр."""
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", self.value):
            raise FunnelError("Цвет должен иметь формат #RRGGBB.")
        object.__setattr__(self, "value", self.value.upper())
