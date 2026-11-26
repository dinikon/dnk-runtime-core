from src.modules.feed_builder.domain.feed.expression.value_object.boolean_calculation import (
    BooleanCalculationVO,
)
from src.modules.feed_builder.domain.feed.field_node.boolean.value_object.data import (
    BooleanNodeDataVO,
)
from src.modules.feed_builder.domain.feed.value_object.constant_value_definition import (
    ConstantValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.field_node.integer.value_object.data import (
    IntegerNodeDataVO,
)
from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.application.feed.graph.error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.domain.feed.value_object.source_value_definition import (
    SourceValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.manual_value_definition import (
    ManualValueDefinitionVO,
)
from src.modules.feed_builder.application.feed.graph.json_values import document
from src.modules.feed_builder.application.feed.graph.expression_codec import (
    ExpressionReader,
    node_document,
)
from src.modules.feed_builder.application.feed.graph.field_settings_codec import (
    decode_source,
    source_document,
)


def read_numeric_bool(raw_type: JsonObject) -> IntegerNodeDataVO | BooleanNodeDataVO:
    """Восстанавливает типизированную конфигурацию ноды."""
    kind = raw_type.get("kind")
    definition = document(raw_type, {"kind", "value"}, {"constraints"})
    constraints = document(
        definition.get("constraints", {}),
        set(),
        ({"required", "min_value", "max_value"} if kind == "integer" else {"required"}),
    )
    raw_value = document(
        definition["value"],
        {"kind"},
        {"source", "value", "condition", "then_value", "else_value"},
    )
    match raw_value["kind"]:
        case "SOURCE":
            source = document(raw_value, {"kind", "source"})
            scalar = SourceValueDefinitionVO(decode_source(source["source"]))
        case "MANUAL":
            document(raw_value, {"kind"})
            scalar = ManualValueDefinitionVO()
        case "CONSTANT":
            constant = document(raw_value, {"kind", "value"})
            scalar = ConstantValueDefinitionVO(constant["value"])
        case "CALCULATED" if kind == "boolean":
            conditional = document(
                raw_value, {"kind", "condition", "then_value", "else_value"}
            )
            scalar = BooleanCalculationVO(
                ExpressionReader().node(conditional["condition"]),
                conditional["then_value"],
                conditional["else_value"],
            )
        case _:
            raise InvalidFeedSchemaDocumentError(
                "Неизвестное определение значения поля."
            )
    required = constraints.get("required", False)
    if kind == "integer":
        field_type = IntegerNodeDataVO(
            scalar,
            required,
            constraints.get("min_value"),
            constraints.get("max_value"),
        )
    else:
        field_type = BooleanNodeDataVO(scalar, required)
    return field_type


def write_numeric_bool(definition: IntegerNodeDataVO | BooleanNodeDataVO) -> JsonObject:
    """Представляет настройки ноды для JSON-документа."""
    settings: JsonObject = {"kind": definition.kind.value}
    scalar_constraints: JsonObject = {"required": definition.required}
    if isinstance(definition, IntegerNodeDataVO):
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
    return settings
