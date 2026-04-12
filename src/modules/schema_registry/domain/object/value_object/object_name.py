from dataclasses import dataclass
import re

from src.modules.schema_registry.domain.error import InvalidValueObjectError

_PG_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _validate_pg_identifier(value: str, *, field_name: str) -> str:
    """Валидирует имя объекта как PostgreSQL-идентификатор."""
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
        raise InvalidValueObjectError(f"{field_name} must be lowercase.")

    if not _PG_IDENTIFIER_RE.match(normalized):
        raise InvalidValueObjectError(f"{field_name} must match ^[a-z][a-z0-9_]*$")

    return normalized


@dataclass(frozen=True, slots=True)
class ObjectNameVO:
    """Value object для singular/plural имен runtime-объекта."""

    singular: str
    plural: str

    def __post_init__(self) -> None:
        """Нормализует имена и проверяет правила plural runtime-таблицы."""
        normalized_singular = _validate_pg_identifier(
            self.singular,
            field_name="Object singular_name",
        )
        normalized_plural = _validate_pg_identifier(
            self.plural,
            field_name="Object plural_name",
        )

        if normalized_singular == normalized_plural:
            raise InvalidValueObjectError(
                "Object singular_name must not be equal to plural_name."
            )

        if not normalized_plural.endswith("s"):
            raise InvalidValueObjectError("Object plural_name must end with 's'.")

        object.__setattr__(self, "singular", normalized_singular)
        object.__setattr__(self, "plural", normalized_plural)
