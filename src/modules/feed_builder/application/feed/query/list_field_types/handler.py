from src.modules.feed_builder.application.feed.query.list_field_types.query import (
    ListFieldTypesQuery,
)
from src.modules.feed_builder.application.feed.query.list_field_types.dto import (
    ListFieldTypesResultDTO,
    FieldTypeItemDTO,
)
from src.modules.feed_builder.application.feed.port.schema_locales import (
    SchemaLocalesPort,
)
from src.modules.feed_builder.domain.feed.limits import MAX_FIELDS, MAX_TRANSFORMS
from src.modules.feed_builder.domain.feed.enum.field_value_type import FieldValueType


class ListFieldTypesHandler:
    """Собирает возможности типов и доступные локали через Application port."""

    def __init__(self, locales: SchemaLocalesPort) -> None:
        """Принимает порт справочника без SQL-зависимостей."""
        self._locales = locales

    async def execute(self, query: ListFieldTypesQuery) -> ListFieldTypesResultDTO:
        """Возвращает только реализованные режимы редактирования определения."""
        labels = {
            FieldValueType.STRING: "Короткий текст",
            FieldValueType.TEXT: "Длинный текст",
            FieldValueType.MONEY: "Денежное значение",
            FieldValueType.INTEGER: "Целое число",
            FieldValueType.BOOLEAN: "Логическое значение",
            FieldValueType.CATEGORY: "Категория",
        }
        modes = ("SOURCE", "MANUAL", "CONSTANT")
        specialized_modes = {
            FieldValueType.MONEY: ("SOURCE", "MANUAL", "CALCULATED"),
            FieldValueType.BOOLEAN: (*modes, "CALCULATED"),
            FieldValueType.CATEGORY: ("INLINE",),
        }
        return ListFieldTypesResultDTO(
            tuple(
                FieldTypeItemDTO(
                    kind.value,
                    labels[kind],
                    kind in (FieldValueType.STRING, FieldValueType.TEXT),
                    kind is FieldValueType.MONEY,
                    specialized_modes.get(kind, modes),
                )
                for kind in FieldValueType
            ),
            await self._locales.list_available(),
            MAX_FIELDS,
            MAX_TRANSFORMS,
        )
