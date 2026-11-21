from __future__ import annotations
from typing import TYPE_CHECKING
from src.modules.feed_builder.domain.feed.entity.conditional_price_rule import (
    ConditionalPriceRule,
)
from src.modules.feed_builder.domain.feed.error import (
    DefinitionStructureLimitExceededError,
    DuplicatePriceRuleIdentifierError,
    InvalidPriceCalculationDefinitionError,
)
from src.modules.feed_builder.domain.feed.limits import MAX_AST_DEPTH, MAX_AST_NODES
from src.modules.feed_builder.domain.feed.value_object.parameter_reference import (
    ParameterReferenceVO,
)
from src.modules.feed_builder.domain.feed.value_object.arithmetic_expression import (
    ArithmeticExpressionVO,
)
from src.modules.feed_builder.domain.feed.value_object.function_expression import (
    FunctionExpressionVO,
)
from src.modules.feed_builder.domain.feed.value_object.comparison_condition import (
    ComparisonConditionVO,
)
from src.modules.feed_builder.domain.feed.value_object.logical_condition import (
    LogicalConditionVO,
)
from src.modules.feed_builder.domain.feed.value_object.presence_condition import (
    PresenceConditionVO,
)
from src.modules.feed_builder.domain.feed.value_object.collection_literal import (
    CollectionLiteralVO,
)
from src.modules.feed_builder.domain.feed.value_object.scalar_literal import (
    ScalarLiteralVO,
)
from src.modules.feed_builder.domain.feed.value_object.decimal_literal import (
    DecimalLiteralVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_literal import (
    MoneyLiteralVO,
)

if TYPE_CHECKING:
    from src.modules.feed_builder.domain.feed.value_object.price_calculation import (
        PriceCalculationVO,
    )


class PriceCalculationStructurePolicy:
    """Проверяет состав расчёта без арифметики, выбора IF или внешних метаданных."""

    @staticmethod
    def ensure_valid(calculation: PriceCalculationVO) -> None:
        """Проверяет ID правил, бюджет дерева и явную закупочную привязку."""
        seen = set()
        stack: list[tuple[object, int, tuple[str | int, ...]]] = [
            (calculation.default_expression, 1, ("default_expression",))
        ]
        for index, rule in enumerate(calculation.rules):
            ConditionalPriceRule.restore(
                identifier=rule.id,
                condition=rule.condition,
                expression=rule.expression,
            )
            if rule.id in seen:
                raise DuplicatePriceRuleIdentifierError(
                    "Rule ID повторяется в расчёте.", path=("rules", index, "id")
                )
            seen.add(rule.id)
            stack.extend(
                (
                    (rule.condition, 1, ("rules", index, "condition")),
                    (rule.expression, 1, ("rules", index, "expression")),
                )
            )
        count = 0
        uses_purchase = False
        while stack:
            node, depth, path = stack.pop()
            count += 1
            if depth > MAX_AST_DEPTH or count > MAX_AST_NODES:
                raise DefinitionStructureLimitExceededError(
                    "Превышена глубина или число узлов расчёта.", path=path
                )
            children: tuple[tuple[tuple[str | int, ...], object], ...] = ()
            if isinstance(node, ParameterReferenceVO):
                uses_purchase = uses_purchase or node.parameter == "price.purchase"
            elif isinstance(node, ArithmeticExpressionVO):
                children = (
                    ((("operand",), node.operand),)
                    if node.operand is not None
                    else ((("left",), node.left), (("right",), node.right))
                )
            elif isinstance(node, FunctionExpressionVO):
                children = tuple(
                    (("arguments", index), child)
                    for index, child in enumerate(node.arguments)
                )
            elif isinstance(node, ComparisonConditionVO):
                children = ((("left",), node.left), (("right",), node.right))
            elif isinstance(node, LogicalConditionVO):
                children = tuple(
                    (("operands", index), child)
                    for index, child in enumerate(node.operands)
                )
            elif isinstance(node, PresenceConditionVO):
                children = ((("parameter",), node.parameter),)
            elif isinstance(node, CollectionLiteralVO):
                children = tuple(
                    (("items", index), child) for index, child in enumerate(node.items)
                )
            elif not isinstance(
                node, (ScalarLiteralVO, DecimalLiteralVO, MoneyLiteralVO)
            ):
                raise InvalidPriceCalculationDefinitionError(
                    "Неизвестный узел определения.", path=path
                )
            stack.extend(
                (child, depth + 1, (*path, *relative_path))
                for relative_path, child in children
            )
        if uses_purchase != (calculation.purchase_source is not None):
            raise InvalidPriceCalculationDefinitionError(
                "Закупочный источник требуется только при зависимости price.purchase.",
                path=("purchase_source",),
            )
