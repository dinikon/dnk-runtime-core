from src.modules.feed_builder.domain.feed.expression.parameters import parameter_type
from src.modules.feed_builder.domain.feed.expression.error import (
    CalculationDefinitionError,
)
from src.modules.feed_builder.domain.feed.expression.structure_policy import (
    PriceCalculationStructurePolicy,
)
from src.modules.feed_builder.domain.feed.expression.value_object.price_calculation import (
    PriceCalculationVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.parameter_reference import (
    ParameterReferenceVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.decimal_literal import (
    DecimalLiteralVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.scalar_literal import (
    ScalarLiteralVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.collection_literal import (
    CollectionLiteralVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.arithmetic_expression import (
    ArithmeticExpressionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.function_expression import (
    FunctionExpressionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.comparison_condition import (
    ComparisonConditionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.logical_condition import (
    LogicalConditionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.presence_condition import (
    PresenceConditionVO,
)


class PriceCalculationSemanticPolicy:
    """Проверяет типы и зависимости всего AST до чтения данных и исполнения ветвей."""

    @classmethod
    def ensure_valid(cls, calculation: PriceCalculationVO) -> None:
        """Проверяет все ветви и отклоняет устаревшую привязку закупки."""
        PriceCalculationStructurePolicy.ensure_valid(calculation)
        if calculation.purchase_source is not None:
            raise CalculationDefinitionError(
                "UNKNOWN_CALCULATION_PARAMETER",
                "Используйте price.purchase из Catalog без закупочной привязки.",
                path=("purchase_source",),
            )
        cls._require(
            cls.node_type(calculation.default_expression, ("default_expression",))
            == "number",
            ("default_expression",),
        )
        for index, rule in enumerate(calculation.rules):
            cls._require(
                cls.node_type(rule.condition, ("rules", index, "condition"))
                == "condition",
                ("rules", index, "condition"),
            )
            cls._require(
                cls.node_type(rule.expression, ("rules", index, "expression"))
                == "number",
                ("rules", index, "expression"),
            )

    @classmethod
    def ensure_condition(cls, condition: object) -> None:
        """Проверяет, что корень логического расчёта возвращает условие."""
        path = ("condition",)
        cls._require(cls.node_type(condition, path) == "condition", path)

    @staticmethod
    def _require(valid: bool, path: tuple[str | int, ...]) -> None:
        """Запрещает несовместимые типы независимо от значений конкретного товара."""
        if not valid:
            raise CalculationDefinitionError(
                "INVALID_EXPRESSION_TYPE",
                "Типы операндов несовместимы с операцией.",
                path=path,
            )

    @classmethod
    def node_type(cls, node: object, path: tuple[str | int, ...]) -> str:
        """Выводит тип закрытого узла без динамического доступа или вычисления значений."""
        if isinstance(node, ParameterReferenceVO):
            return parameter_type(node.parameter, path)
        if isinstance(node, DecimalLiteralVO):
            return "number"
        if isinstance(node, ScalarLiteralVO):
            return node.value_type.value
        if isinstance(node, CollectionLiteralVO):
            return "collection:" + node.item_type.value
        if isinstance(node, ArithmeticExpressionVO):
            operands = (
                (("operand", node.operand),)
                if node.operand is not None
                else (("left", node.left), ("right", node.right))
            )
            for name, operand in operands:
                cls._require(
                    cls.node_type(operand, (*path, name)) == "number", (*path, name)
                )
            return "number"
        if isinstance(node, FunctionExpressionVO):
            for index, operand in enumerate(node.arguments):
                cls._require(
                    cls.node_type(operand, (*path, "arguments", index)) == "number",
                    (*path, "arguments", index),
                )
            return "number"
        if isinstance(node, PresenceConditionVO):
            parameter_type(node.parameter.parameter, (*path, "parameter"))
            return "condition"
        if isinstance(node, LogicalConditionVO):
            for index, operand in enumerate(node.operands):
                cls._require(
                    cls.node_type(operand, (*path, "operands", index)) == "condition",
                    (*path, "operands", index),
                )
            return "condition"
        if isinstance(node, ComparisonConditionVO):
            left = cls.node_type(node.left, (*path, "left"))
            right = cls.node_type(node.right, (*path, "right"))
            op = node.operator.value
            if op == "CONTAINS" and left.startswith("collection:"):
                expected = left.removeprefix("collection:")
                if right != expected:
                    raise CalculationDefinitionError(
                        "INVALID_EXPRESSION_TYPE",
                        f"Оператор CONTAINS ожидает справа значение типа {expected}.",
                        path=(*path, "right"),
                    )
                return "condition"
            valid = (
                (left == right and not left.startswith("collection:"))
                if op in ("EQ", "NE")
                else (
                    (left == right == "number")
                    if op in ("GT", "GTE", "LT", "LTE")
                    else (
                        right == "collection:" + left
                        if op in ("IN", "NOT_IN")
                        else left == "collection:" + right
                    )
                )
            )
            cls._require(valid, path)
            return "condition"
        raise CalculationDefinitionError(
            "INVALID_EXPRESSION_TYPE", "Неизвестный вид узла выражения.", path=path
        )
