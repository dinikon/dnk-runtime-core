from __future__ import annotations

import re
from dataclasses import dataclass

from src.modules.custom_object.domain.errors import (
    CustomObjectNameInvalidError,
    CustomObjectNameRequiredError,
)


@dataclass(frozen=True, slots=True)
class CustomObjectNameVO:
    value: str

    _SNAKE_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not normalized:
            raise CustomObjectNameRequiredError()
        if not self._SNAKE_CASE_PATTERN.match(normalized):
            raise CustomObjectNameInvalidError(self.value)
        object.__setattr__(self, "value", normalized)


__all__ = ["CustomObjectNameVO"]
