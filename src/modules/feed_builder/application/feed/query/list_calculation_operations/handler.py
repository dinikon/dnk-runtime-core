from src.modules.feed_builder.application.feed.query.list_calculation_operations.query import (
    ListCalculationOperationsQuery,
)
from src.modules.feed_builder.application.feed.query.list_calculation_operations.dto import (
    ListCalculationOperationsResultDTO,
    CalculationOperationDTO,
)
from src.modules.feed_builder.domain.feed.expression.enum.arithmetic_operator import (
    ArithmeticOperator,
)
from src.modules.feed_builder.domain.feed.expression.enum.price_function import PriceFunction
from src.modules.feed_builder.domain.feed.expression.enum.comparison_operator import (
    ComparisonOperator,
)
from src.modules.feed_builder.domain.feed.expression.enum.logical_operator import LogicalOperator
from src.modules.feed_builder.domain.feed.expression.enum.presence_operator import PresenceOperator
from src.modules.feed_builder.domain.feed.expression.parameters import (
    ENGINE_VERSION,
    PRECISION,
)
from src.modules.feed_builder.domain.feed.limits import (
    MAX_AST_DEPTH,
    MAX_AST_NODES,
    MAX_RULES,
    MAX_COLLECTION_ITEMS,
)


class ListCalculationOperationsHandler:
    """Описывает только операции, исполняемые текущим вычислителем."""

    async def execute(
        self, query: ListCalculationOperationsQuery
    ) -> ListCalculationOperationsResultDTO:
        """Возвращает арность и лимиты, сохраняя Enum-коды Domain."""
        labels = {
            "ADD": "Сложить",
            "SUBTRACT": "Вычесть",
            "MULTIPLY": "Умножить",
            "DIVIDE": "Разделить",
            "NEGATE": "Изменить знак",
            "MIN": "Минимум",
            "MAX": "Максимум",
            "ABS": "Модуль",
            "EQ": "Равно",
            "NE": "Не равно",
            "GT": "Больше",
            "GTE": "Не меньше",
            "LT": "Меньше",
            "LTE": "Не больше",
            "IN": "Входит в список",
            "NOT_IN": "Не входит в список",
            "CONTAINS": "Содержит",
            "ALL": "Все условия (AND)",
            "ANY": "Любое условие (OR)",
            "NOT": "Не",
            "EXISTS": "Значение есть",
            "IS_MISSING": "Значения нет",
        }
        operations: list[CalculationOperationDTO] = []
        for category, entries in (
            ("arithmetic", ArithmeticOperator),
            ("function", PriceFunction),
            ("comparison", ComparisonOperator),
            ("logical", LogicalOperator),
            ("presence", PresenceOperator),
        ):
            for entry in entries:
                low, high = (
                    (1, 1)
                    if entry.value in {"NEGATE", "ABS", "NOT", "EXISTS", "IS_MISSING"}
                    else (
                        (2, MAX_AST_NODES)
                        if category == "function"
                        else (1, MAX_AST_NODES) if category == "logical" else (2, 2)
                    )
                )
                operations.append(
                    CalculationOperationDTO(
                        entry.value, category, labels[entry.value], low, high
                    )
                )
        return ListCalculationOperationsResultDTO(
            tuple(operations),
            ENGINE_VERSION,
            PRECISION,
            MAX_AST_DEPTH,
            MAX_AST_NODES,
            MAX_RULES,
            MAX_COLLECTION_ITEMS,
        )
