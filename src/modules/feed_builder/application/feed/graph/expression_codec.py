from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.domain.feed.limits import (
    MAX_AST_DEPTH,
    MAX_AST_NODES,
    MAX_COLLECTION_ITEMS,
    MAX_RULES,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.feed_builder.domain.feed.types import (
    Condition,
    ConditionOperand,
    Expression,
)
from src.modules.feed_builder.application.feed.graph.error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.domain.feed.expression.entity.conditional_price_rule import (
    ConditionalPriceRule,
)
from src.modules.feed_builder.domain.feed.expression.enum.arithmetic_operator import (
    ArithmeticOperator,
)
from src.modules.feed_builder.domain.feed.expression.enum.comparison_operator import (
    ComparisonOperator,
)
from src.modules.feed_builder.domain.feed.expression.enum.logical_operator import (
    LogicalOperator,
)
from src.modules.feed_builder.domain.feed.expression.enum.presence_operator import (
    PresenceOperator,
)
from src.modules.feed_builder.domain.feed.expression.enum.literal_value_type import (
    LiteralValueType,
)
from src.modules.feed_builder.domain.feed.expression.enum.price_function import (
    PriceFunction,
)
from src.modules.feed_builder.domain.feed.expression.value_object.price_calculation import (
    PriceCalculationVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.purchase_price_source import (
    PurchasePriceSourceVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.price_rule_id import (
    PriceRuleIdVO,
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
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError
from src.modules.feed_builder.application.feed.graph.json_values import (
    array,
    document,
    optional_decimal,
    string,
)


class ExpressionReader:
    """Декодирует AST с ограничениями глубины и числа узлов до построения Domain."""

    def __init__(self) -> None:
        """Создаёт отдельный бюджет одного расчёта."""
        self.nodes = 0

    def node(
        self, value: object, depth: int = 1
    ) -> Expression | ConditionOperand | Condition:
        """Восстанавливает конкретный узел без динамического поиска Python-атрибутов."""
        self.nodes += 1
        if depth > MAX_AST_DEPTH or self.nodes > MAX_AST_NODES:
            raise InvalidFeedSchemaDocumentError("Превышен бюджет AST.")
        if not isinstance(value, dict):
            raise InvalidFeedSchemaDocumentError("Узел AST должен быть объектом.")
        kind = value.get("kind")
        if kind == "parameter":
            data = document(value, {"kind", "parameter"})
            return ParameterReferenceVO(string(data["parameter"]))
        if kind == "decimal":
            data = document(value, {"kind", "value"})
            return DecimalLiteralVO(optional_decimal(data["value"]))
        if kind == "scalar":
            data = document(value, {"kind", "value_type", "value"})
            value_type = LiteralValueType(string(data["value_type"]))
            scalar = data["value"]
            if value_type is LiteralValueType.UUID:
                scalar = EntityIdVO.from_value(string(scalar))
            return ScalarLiteralVO(value_type, scalar)
        if kind == "collection":
            data = document(value, {"kind", "item_type", "items"})
            return CollectionLiteralVO(
                LiteralValueType(string(data["item_type"])),
                tuple(
                    self.node(item, depth + 1)
                    for item in array(data["items"], MAX_COLLECTION_ITEMS)
                ),
            )
        if kind == "arithmetic":
            operator = ArithmeticOperator(string(value.get("operator")))
            if operator is ArithmeticOperator.NEGATE:
                data = document(value, {"kind", "operator", "operand"})
                return ArithmeticExpressionVO(
                    operator, operand=self.node(data["operand"], depth + 1)
                )
            data = document(value, {"kind", "operator", "left", "right"})
            return ArithmeticExpressionVO(
                operator,
                left=self.node(data["left"], depth + 1),
                right=self.node(data["right"], depth + 1),
            )
        if kind == "function":
            data = document(value, {"kind", "function", "arguments"})
            return FunctionExpressionVO(
                PriceFunction(string(data["function"])),
                tuple(
                    self.node(item, depth + 1)
                    for item in array(data["arguments"], MAX_AST_NODES)
                ),
            )
        if kind == "comparison":
            data = document(value, {"kind", "operator", "left", "right"})
            return ComparisonConditionVO(
                ComparisonOperator(string(data["operator"])),
                self.node(data["left"], depth + 1),
                self.node(data["right"], depth + 1),
            )
        if kind == "logical":
            data = document(value, {"kind", "operator", "operands"})
            return LogicalConditionVO(
                LogicalOperator(string(data["operator"])),
                tuple(
                    self.node(item, depth + 1)
                    for item in array(data["operands"], MAX_AST_NODES)
                ),
            )
        if kind == "presence":
            data = document(value, {"kind", "operator", "parameter"})
            return PresenceConditionVO(
                PresenceOperator(string(data["operator"])),
                ParameterReferenceVO(string(data["parameter"])),
            )
        raise InvalidFeedSchemaDocumentError("Неизвестный вид узла AST.")

    def calculation(self, value: object) -> PriceCalculationVO:
        """Восстанавливает ELSE, правила и явную привязку закупки."""
        data = document(value, {"default_expression", "rules"}, {"purchase_source"})
        default = self.node(data["default_expression"])
        rules = []
        for item in array(data["rules"], MAX_RULES):
            rule = document(item, {"id", "condition", "expression"})
            rules.append(
                ConditionalPriceRule.restore(
                    identifier=PriceRuleIdVO.from_value(string(rule["id"])),
                    condition=self.node(rule["condition"]),
                    expression=self.node(rule["expression"]),
                )
            )
        purchase_source = None
        if data.get("purchase_source") is not None:
            purchase = document(
                data["purchase_source"], {"provider", "path", "selection"}
            )
            selection = document(purchase["selection"], {"mode", "supplier_source_id"})
            if (
                purchase["provider"] != "supplier_sourcing"
                or purchase["path"] != "purchase_price"
                or selection["mode"] != "SUPPLIER_SOURCE"
            ):
                raise InvalidFeedSchemaDocumentError(
                    "Неизвестная привязка закупочного источника."
                )
            purchase_source = PurchasePriceSourceVO(
                EntityIdVO.from_value(string(selection["supplier_source_id"]))
            )
        return PriceCalculationVO(
            default_expression=default,
            rules=tuple(rules),
            purchase_source=purchase_source,
        )


def node_document(node: Expression | ConditionOperand | Condition) -> JsonObject:
    """Представляет все разрешённые узлы, не вычисляя выражение."""
    if isinstance(node, ParameterReferenceVO):
        return {"kind": "parameter", "parameter": node.parameter}
    if isinstance(node, DecimalLiteralVO):
        return {"kind": "decimal", "value": str(node.value)}
    if isinstance(node, ScalarLiteralVO):
        value = (
            str(node.value.uuid) if isinstance(node.value, EntityIdVO) else node.value
        )
        return {"kind": "scalar", "value_type": node.value_type.value, "value": value}
    if isinstance(node, CollectionLiteralVO):
        return {
            "kind": "collection",
            "item_type": node.item_type.value,
            "items": [node_document(item) for item in node.items],
        }
    if isinstance(node, ArithmeticExpressionVO):
        result: JsonObject = {"kind": "arithmetic", "operator": node.operator.value}
        if node.operand is not None:
            result["operand"] = node_document(node.operand)
        else:
            result["left"] = node_document(node.left)
            result["right"] = node_document(node.right)
        return result
    if isinstance(node, FunctionExpressionVO):
        return {
            "kind": "function",
            "function": node.function.value,
            "arguments": [node_document(item) for item in node.arguments],
        }
    if isinstance(node, ComparisonConditionVO):
        return {
            "kind": "comparison",
            "operator": node.operator.value,
            "left": node_document(node.left),
            "right": node_document(node.right),
        }
    if isinstance(node, LogicalConditionVO):
        return {
            "kind": "logical",
            "operator": node.operator.value,
            "operands": [node_document(item) for item in node.operands],
        }
    if isinstance(node, PresenceConditionVO):
        return {
            "kind": "presence",
            "operator": node.operator.value,
            "parameter": node.parameter.parameter,
        }
    raise InvalidFeedValueError("Неизвестный узел документа.")


def calculation_document(value: PriceCalculationVO) -> JsonObject:
    """Представляет расчёт с явным ELSE и без валюты вычислений."""
    document: JsonObject = {
        "default_expression": node_document(value.default_expression),
        "rules": [
            {
                "id": str(rule.id.uuid),
                "condition": node_document(rule.condition),
                "expression": node_document(rule.expression),
            }
            for rule in value.rules
        ],
    }
    if value.purchase_source is not None:
        document["purchase_source"] = {
            "provider": "supplier_sourcing",
            "path": "purchase_price",
            "selection": {
                "mode": "SUPPLIER_SOURCE",
                "supplier_source_id": str(
                    value.purchase_source.supplier_source_id.uuid
                ),
            },
        }
    return document
