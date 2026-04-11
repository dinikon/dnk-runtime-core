import re
from dataclasses import dataclass

from src.modules.schema_registry.domain.error import InvalidValueObjectError


@dataclass(frozen=True, slots=True)
class SchemaNameVO:
    value: str

    _PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,62}$")

    def __post_init__(self) -> None:
        normalized = self.value.strip()

        if not normalized:
            raise InvalidValueObjectError("Schema name cannot be empty.")

        if normalized != self.value:
            raise InvalidValueObjectError(
                "Schema name must not contain leading or trailing spaces."
            )

        if not self._PATTERN.fullmatch(normalized):
            raise InvalidValueObjectError(
                "Schema name must start with a lowercase letter and contain only "
                "lowercase letters, digits, and underscores, max length 63."
            )

    def __str__(self) -> str:
        return self.value
