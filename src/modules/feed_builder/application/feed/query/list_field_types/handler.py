from src.modules.feed_builder.application.feed.graph.forms import node_forms
from src.modules.feed_builder.application.feed.graph.registry import NODE_CODECS
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
        return ListFieldTypesResultDTO(
            tuple(
                FieldTypeItemDTO(
                    codec.kind.value,
                    codec.label,
                    codec.kind
                    in (
                        FieldValueType.STRING,
                        FieldValueType.TEXT,
                        FieldValueType.RICH_TEXT,
                    ),
                    codec.kind is FieldValueType.MONEY,
                    codec.modes,
                    codec.type_id,
                    codec.version,
                    node_forms(codec),
                )
                for codec in NODE_CODECS
            ),
            await self._locales.list_available(),
            MAX_FIELDS,
            MAX_TRANSFORMS,
        )
