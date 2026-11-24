"""Чистое представление Domain-схемы в версионируемом документе результатов."""

from src.modules.feed_builder.domain.feed.value_object.category_field_type import (
    CategoryFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.enum.xml_field_placement import (
    XmlFieldPlacement,
)
from src.modules.feed_builder.domain.feed.value_object.text_constant_value_definition import (
    TextConstantValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.boolean_calculation import (
    BooleanCalculationVO,
)
from src.modules.feed_builder.domain.feed.value_object.boolean_field_type import (
    BooleanFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.constant_value_definition import (
    ConstantValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.integer_field_type import (
    IntegerFieldTypeVO,
)
from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.feed_builder.domain.feed.types import (
    Condition,
    ConditionOperand,
    Expression,
)
from src.modules.feed_builder.domain.feed.entity.field_definition import FieldDefinition
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.domain.feed.value_object.source_reference import (
    SourceReferenceVO,
)
from src.modules.feed_builder.domain.feed.value_object.source_value_definition import (
    SourceValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_field_type import (
    MoneyFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.price_calculation import (
    PriceCalculationVO,
)
from src.modules.feed_builder.domain.feed.value_object.parameter_reference import (
    ParameterReferenceVO,
)
from src.modules.feed_builder.domain.feed.value_object.decimal_literal import (
    DecimalLiteralVO,
)
from src.modules.feed_builder.domain.feed.value_object.scalar_literal import (
    ScalarLiteralVO,
)
from src.modules.feed_builder.domain.feed.value_object.collection_literal import (
    CollectionLiteralVO,
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
from src.modules.feed_builder.domain.feed.value_object.transform_definition import (
    TransformDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.truncate_parameters import (
    TruncateParametersVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_ceil_step_parameters import (
    MoneyCeilStepParametersVO,
)
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


def source_document(source: SourceReferenceVO) -> JsonObject:
    """Представляет типизированный прямой источник без чтения данных."""
    return {"provider": source.provider.value, "path": source.path.value}


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


def transform_document(value: TransformDefinitionVO) -> JsonObject:
    """Представляет параметры преобразования без выполнения."""
    parameters: JsonObject = {}
    if isinstance(value.parameters, TruncateParametersVO):
        parameters = {"max_length": value.parameters.max_length}
    elif isinstance(value.parameters, MoneyCeilStepParametersVO):
        parameters = {"step": str(value.parameters.step)}
    return {"op": value.operation.value, "params": parameters}


def field_document(value: FieldDefinition) -> JsonObject:
    """Представляет поле с единственным вложенным описанием типа."""
    definition = value.type_definition
    settings: JsonObject = {"kind": definition.kind.value}
    if isinstance(definition, CategoryFieldTypeVO):
        settings = category_field_document(definition)
    elif isinstance(definition, (IntegerFieldTypeVO, BooleanFieldTypeVO)):
        scalar_constraints: JsonObject = {"required": definition.required}
        if isinstance(definition, IntegerFieldTypeVO):
            scalar_constraints.update(
                min_value=definition.min_value, max_value=definition.max_value
            )
        settings["constraints"] = scalar_constraints
        scalar = definition.value_definition
        if isinstance(scalar, SourceValueDefinitionVO):
            settings["value"] = {
                "kind": "SOURCE",
                "source": source_document(scalar.source),
            }
        elif isinstance(scalar, ConstantValueDefinitionVO):
            settings["value"] = {"kind": "CONSTANT", "value": scalar.value}
        elif isinstance(scalar, BooleanCalculationVO):
            settings["value"] = {
                "kind": "CALCULATED",
                "condition": node_document(scalar.condition),
                "then_value": scalar.then_value,
                "else_value": scalar.else_value,
            }
        else:
            settings["value"] = {"kind": "MANUAL"}
    elif isinstance(definition, MoneyFieldTypeVO):
        settings["currency"] = (
            definition.currency.value if definition.currency is not None else None
        )
        constraints = definition.constraints
        settings["constraints"] = {
            "required": constraints.required,
            "min_amount": (
                str(constraints.min_amount)
                if constraints.min_amount is not None
                else None
            ),
            "max_amount": (
                str(constraints.max_amount)
                if constraints.max_amount is not None
                else None
            ),
        }
        money = definition.value_definition
        money_value: JsonObject = {"kind": "MONEY", "mode": money.mode.value}
        if money.source is not None:
            money_value["source"] = source_document(money.source)
        if money.calculation is not None:
            money_value["calculation"] = calculation_document(money.calculation)
        settings["value"] = money_value
    else:
        settings["locale"] = (
            definition.locale.value if definition.locale is not None else None
        )
        settings["fallback_policy"] = (
            {
                "mode": definition.fallback_policy.mode.value,
                "locales": [
                    locale.value for locale in definition.fallback_policy.locales
                ],
            }
            if definition.fallback_policy is not None
            else None
        )
        settings["constraints"] = {
            "required": definition.constraints.required,
            "min_length": definition.constraints.min_length,
            "max_length": definition.constraints.max_length,
        }
        text = definition.value_definition
        if isinstance(text, SourceValueDefinitionVO):
            settings["value"] = {
                "kind": "SOURCE",
                "source": source_document(text.source),
            }
        elif isinstance(text, TextConstantValueDefinitionVO):
            settings["value"] = {"kind": "CONSTANT", "value": text.value}
        else:
            settings["value"] = {"kind": "MANUAL"}
    if not isinstance(
        definition, (IntegerFieldTypeVO, BooleanFieldTypeVO, CategoryFieldTypeVO)
    ):
        settings["transforms"] = [
            transform_document(item) for item in definition.transforms
        ]
    export: JsonObject = {
        "name": value.export.name.value,
        "enabled": value.export.enabled,
    }
    if value.export.xml_placement is XmlFieldPlacement.ATTRIBUTE:
        export["xml_placement"] = value.export.xml_placement.value
    if value.export.document is not None:
        layout = value.export.document
        export["document"] = {
            "container": layout.container.value,
            "item": layout.item.value,
            "parent": layout.parent,
            "layout": layout.layout,
            "parent_attribute": layout.parent_attribute.value,
        }
    if value.export.publication_key is not None:
        export["publication"] = {
            "value_key": value.export.publication_key.value,
            "required": value.export.required,
        }
    return {
        "id": str(value.id.uuid),
        "key": value.key.value,
        "label": value.label.value,
        "type_definition": settings,
        "export": export,
        "ai": {"instruction": value.ai_instruction},
    }


def category_field_document(value: CategoryFieldTypeVO) -> JsonObject:
    """Представляет описание и данные одного поля категории."""
    return {
        "kind": "category",
        "locale": value.locale.value,
        "name_transforms": [transform_document(item) for item in value.name_transforms],
        "object_schema": {
            "id_key": value.id_key,
            "label_key": value.label_key,
            "fields": [
                {
                    "key": prop.key.value,
                    "kind": prop.kind,
                    "required": prop.required,
                    "xml": {"placement": prop.placement, "name": prop.name.value},
                    "source": prop.source,
                }
                for prop in value.properties
            ],
        },
        "value": {
            "kind": "INLINE",
            "next_export_id": value.next_export_id,
            "nodes": [
                {
                    "id": str(node.id),
                    "values": dict(node.values),
                    "parent_id": str(node.parent_id) if node.parent_id else None,
                    "catalog_id": str(node.catalog_id) if node.catalog_id else None,
                    "inherit_parent": node.inherit_parent,
                }
                for node in value.nodes
            ],
            "rules": [
                {
                    "id": str(rule.id),
                    "target_id": str(rule.target_id),
                    "label": rule.label,
                    "condition": node_document(rule.calculation.condition),
                    "include_descendants": rule.include_descendants,
                }
                for rule in value.rules
            ],
            "fallback": value.fallback,
            "fallback_id": str(value.fallback_id) if value.fallback_id else None,
            "catalog_priority": [
                str(identifier) for identifier in value.catalog_priority
            ],
        },
    }


def schema_document(value: FeedSchemaVO) -> JsonObject:
    """Возвращает порядок и описание полей в рабочей схеме."""
    return {
        "schema_format_version": value.schema_format_version,
        "root": {
            "key": "publication",
            "kind": "object",
            "fields": [field_document(item) for item in value.fields],
        },
    }
