import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SchemaNameVO:
    value: str

    _PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")

    def __post_init__(self) -> None:
        normalized = self.value.lower()

        if not self._PATTERN.fullmatch(normalized):
            raise ValueError("Invalid data_source name format")

        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
