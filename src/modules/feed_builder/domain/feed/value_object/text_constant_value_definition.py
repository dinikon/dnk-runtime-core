from dataclasses import dataclass

from src.modules.feed_builder.domain.feed.error import InvalidFieldDefinitionError


@dataclass(frozen=True, slots=True)
class TextConstantValueDefinitionVO:
    """Хранит текст, заданный в схеме для всех публикаций."""

    value: str

    def __post_init__(self) -> None:
        """Принимает только строковое значение без приведения типа."""
        if not isinstance(self.value, str):
            raise InvalidFieldDefinitionError(
                "Задайте текстовое значение.",
                path=("type_definition", "value", "value"),
            )
