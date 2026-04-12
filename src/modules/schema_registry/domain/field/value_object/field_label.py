from dataclasses import dataclass

from src.modules.schema_registry.domain.error import InvalidValueObjectError


def validate_label(value: str, *, field_name: str, max_length: int = 16) -> str:
    """Валидирует человекочитаемый label и возвращает trim-значение."""

    normalized = value.strip()

    if not normalized:
        raise InvalidValueObjectError(f"{field_name} cannot be empty.")

    if len(normalized) > max_length:
        raise InvalidValueObjectError(f"{field_name} length must be <= {max_length}.")

    return normalized


@dataclass(frozen=True, slots=True)
class FieldLabelVO:
    """Value object для короткого человекочитаемого label поля."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует и валидирует label поля."""
        normalized = validate_label(
            self.value,
            field_name="Field label",
            max_length=16,
        )
        object.__setattr__(self, "value", normalized)
