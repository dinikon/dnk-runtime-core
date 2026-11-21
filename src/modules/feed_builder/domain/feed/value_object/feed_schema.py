from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.entity.field_definition import FieldDefinition
from src.modules.feed_builder.domain.feed.limits import MAX_FIELDS
from src.modules.feed_builder.domain.feed.validation import sequence
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class FeedSchemaVO:
    """Хранит полный упорядоченный снимок полей, включая пустую схему."""

    fields: tuple[FieldDefinition, ...] = ()
    schema_format_version: int = 1

    def __post_init__(self) -> None:
        """Замораживает состав; уникальность полей обеспечивает корневой агрегат."""
        fields = sequence(self.fields, label="Feed fields", maximum=MAX_FIELDS)
        if (
            not all(isinstance(value, FieldDefinition) for value in fields)
            or type(self.schema_format_version) is not int
            or self.schema_format_version != 1
        ):
            raise InvalidFeedValueError(
                "Нужны FieldDefinition и поддержанный формат схемы 1."
            )
        object.__setattr__(self, "fields", fields)
