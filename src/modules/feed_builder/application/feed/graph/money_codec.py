from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.domain.feed.limits import MAX_TRANSFORMS
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.feed_builder.application.feed.graph.error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.domain.feed.enum.money_value_mode import MoneyValueMode
from src.modules.feed_builder.domain.feed.field_node.money.value_object.data import (
    MoneyNodeDataVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_value_definition import (
    MoneyValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_constraints import (
    MoneyConstraintsVO,
)
from src.modules.feed_builder.application.feed.graph.json_values import (
    array,
    boolean,
    document,
    optional_decimal,
    string,
)
from src.modules.feed_builder.application.feed.graph.expression_codec import (
    ExpressionReader,
    calculation_document,
)
from src.modules.feed_builder.application.feed.graph.field_settings_codec import (
    decode_source,
    decode_transform,
    source_document,
    transform_document,
)


def read_money(raw_type: JsonObject) -> MoneyNodeDataVO:
    """Восстанавливает типизированную конфигурацию ноды."""
    transforms = tuple(
        decode_transform(item)
        for item in array(raw_type.get("transforms", []), MAX_TRANSFORMS)
    )
    definition = document(
        raw_type, {"kind", "value"}, {"currency", "constraints", "transforms"}
    )
    constraints = document(
        definition.get("constraints", {}),
        set(),
        {"required", "min_amount", "max_amount"},
    )
    amount = document(definition["value"], {"kind", "mode"}, {"source", "calculation"})
    if amount["kind"] != "MONEY":
        raise InvalidFeedSchemaDocumentError("Неверный вид денежного определения.")
    value_definition = MoneyValueDefinitionVO(
        mode=MoneyValueMode(string(amount["mode"])),
        source=decode_source(amount["source"]) if "source" in amount else None,
        calculation=(
            ExpressionReader().calculation(amount["calculation"])
            if "calculation" in amount
            else None
        ),
    )
    field_type = MoneyNodeDataVO(
        value_definition=value_definition,
        currency=(
            CurrencyVO(string(definition["currency"]))
            if definition.get("currency") is not None
            else None
        ),
        constraints=MoneyConstraintsVO(
            required=boolean(
                constraints.get("required", False), ("constraints", "required")
            ),
            min_amount=optional_decimal(constraints.get("min_amount")),
            max_amount=optional_decimal(constraints.get("max_amount")),
        ),
        transforms=transforms,
    )
    return field_type


def write_money(definition: MoneyNodeDataVO) -> JsonObject:
    """Представляет настройки ноды для JSON-документа."""
    settings: JsonObject = {"kind": definition.kind.value}
    settings["currency"] = (
        definition.currency.value if definition.currency is not None else None
    )
    constraints = definition.constraints
    settings["constraints"] = {
        "required": constraints.required,
        "min_amount": (
            str(constraints.min_amount) if constraints.min_amount is not None else None
        ),
        "max_amount": (
            str(constraints.max_amount) if constraints.max_amount is not None else None
        ),
    }
    money = definition.value_definition
    money_value: JsonObject = {"kind": "MONEY", "mode": money.mode.value}
    if money.source is not None:
        money_value["source"] = source_document(money.source)
    if money.calculation is not None:
        money_value["calculation"] = calculation_document(money.calculation)
    settings["value"] = money_value
    settings["transforms"] = [
        transform_document(item) for item in definition.transforms
    ]
    return settings
