from src.modules.feed_builder.application.feed.query.list_transforms.query import (
    ListTransformsQuery,
)
from src.modules.feed_builder.application.feed.query.list_transforms.dto import (
    ListTransformsResultDTO,
    TransformItemDTO,
)
from src.modules.feed_builder.domain.feed.enum.transform_operation import (
    TransformOperation,
)


class ListTransformsHandler:
    """Описывает существующие преобразования, не вычисляя значения."""

    async def execute(self, query: ListTransformsQuery) -> ListTransformsResultDTO:
        """Возвращает закрытый набор редакторов параметров и совместимых типов."""
        return ListTransformsResultDTO(
            (
                TransformItemDTO(
                    TransformOperation.STRING_TRIM.value,
                    "Убрать пробелы по краям",
                    ("string", "text", "rich_text"),
                    "none",
                ),
                TransformItemDTO(
                    TransformOperation.STRING_TRUNCATE.value,
                    "Обрезать текст",
                    ("string", "text"),
                    "max_length",
                ),
                TransformItemDTO(
                    TransformOperation.MONEY_CEIL_STEP.value,
                    "Округлить вверх до шага",
                    ("money",),
                    "step",
                ),
            )
        )
