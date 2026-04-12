from dataclasses import dataclass
import re

from src.modules.schema_registry.domain.error import InvalidValueObjectError

_PG_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_pg_identifier(value: str, *, field_name: str) -> str:
    """Валидирует PostgreSQL-идентификатор поля или другого schema_registry объекта."""

    normalized = value.strip()

    if not normalized:
        raise InvalidValueObjectError(f"{field_name} cannot be empty.")

    if len(normalized) > 63:
        raise InvalidValueObjectError(
            f"{field_name} is too long. PostgreSQL identifier max length is 63."
        )

    if " " in normalized:
        raise InvalidValueObjectError(f"{field_name} cannot contain spaces.")

    if normalized.lower() != normalized:
        raise InvalidValueObjectError(
            f"{field_name} must contain lowercase letters only."
        )

    if not _PG_IDENTIFIER_RE.match(normalized):
        raise InvalidValueObjectError(
            f"{field_name} must match pattern ^[a-z][a-z0-9_]*$."
        )

    return normalized


@dataclass(frozen=True, slots=True)
class FieldNameVO:
    """Value object для имени поля, пригодного как PostgreSQL-идентификатор."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует и валидирует имя поля."""
        normalized = validate_pg_identifier(
            self.value,
            field_name="Field name",
        )
        object.__setattr__(self, "value", normalized)
