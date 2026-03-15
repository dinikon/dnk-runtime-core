import re
from dataclasses import dataclass

from src.modules.runtime_schema.domain.schema.error import (
    InvalidSchemaNameFormatError,
)


@dataclass(frozen=True, slots=True)
class SchemaNameVO:
    value: str

    _PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise InvalidSchemaNameFormatError(str(self.value))

        normalized = self.value.lower()

        if not self._PATTERN.fullmatch(normalized):
            raise InvalidSchemaNameFormatError(self.value)

        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
