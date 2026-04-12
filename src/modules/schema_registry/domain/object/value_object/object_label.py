from dataclasses import dataclass

from src.modules.schema_registry.domain.error import InvalidValueObjectError


def _validate_label(value: str, *, field_name: str, max_length: int = 16) -> str:
    """Валидирует singular/plural label runtime-объекта."""

    normalized = value.strip()

    if not normalized:
        raise InvalidValueObjectError(f"{field_name} cannot be empty.")

    if len(normalized) > max_length:
        raise InvalidValueObjectError(f"{field_name} length must be <= {max_length}.")

    return normalized


@dataclass(frozen=True, slots=True)
class ObjectLabelVO:
    """Value object для singular/plural человекочитаемых labels объекта."""

    singular: str
    plural: str

    def __post_init__(self) -> None:
        """Нормализует labels и запрещает совпадение singular/plural."""
        normalized_singular = _validate_label(
            self.singular,
            field_name="Object label_singular",
            max_length=16,
        )
        normalized_plural = _validate_label(
            self.plural,
            field_name="Object label_plural",
            max_length=16,
        )

        if normalized_singular == normalized_plural:
            raise InvalidValueObjectError(
                "Object label_singular must not be equal to label_plural."
            )

        object.__setattr__(self, "singular", normalized_singular)
        object.__setattr__(self, "plural", normalized_plural)
