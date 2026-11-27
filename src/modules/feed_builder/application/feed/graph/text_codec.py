from src.modules.feed_builder.domain.feed.value_object.text_constant_value_definition import (
    TextConstantValueDefinitionVO,
)
from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.domain.feed.limits import MAX_TRANSFORMS
from src.modules.feed_builder.application.feed.graph.error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.domain.feed.enum.locale_fallback_mode import (
    LocaleFallbackMode,
)
from src.modules.feed_builder.domain.feed.field_node.short_text.value_object.data import (
    ShortTextNodeDataVO,
)
from src.modules.feed_builder.domain.feed.field_node.long_text.value_object.data import (
    LongTextNodeDataVO,
)
from src.modules.feed_builder.domain.feed.field_node.rich_text.value_object.data import (
    RichTextNodeDataVO,
)
from src.modules.feed_builder.domain.feed.value_object.source_value_definition import (
    SourceValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.manual_value_definition import (
    ManualValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.text_constraints import (
    TextConstraintsVO,
)
from src.modules.feed_builder.domain.feed.value_object.locale_code import LocaleCodeVO
from src.modules.feed_builder.domain.feed.value_object.locale_fallback_policy import (
    LocaleFallbackPolicyVO,
)
from src.modules.feed_builder.application.feed.graph.json_values import (
    array,
    document,
    string,
)
from src.modules.feed_builder.application.feed.graph.field_settings_codec import (
    decode_source,
    decode_transform,
    source_document,
    transform_document,
)


def read_text(raw_type: JsonObject) -> ShortTextNodeDataVO | LongTextNodeDataVO:
    """Восстанавливает типизированную конфигурацию ноды."""
    transforms = tuple(
        decode_transform(item)
        for item in array(raw_type.get("transforms", []), MAX_TRANSFORMS)
    )
    kind = raw_type.get("kind")
    definition = document(
        raw_type,
        {"kind", "value"},
        {"locale", "fallback_policy", "constraints", "transforms"},
    )
    constraints = document(
        definition.get("constraints", {}),
        set(),
        {"required", "min_length", "max_length"},
    )
    text_value = document(definition["value"], {"kind"}, {"source", "value"})
    if text_value["kind"] == "SOURCE":
        text_value = document(text_value, {"kind", "source"})
        value_definition = SourceValueDefinitionVO(decode_source(text_value["source"]))
    elif text_value["kind"] == "MANUAL":
        document(text_value, {"kind"})
        value_definition = ManualValueDefinitionVO()
    elif text_value["kind"] == "CONSTANT":
        constant = document(text_value, {"kind", "value"})
        value_definition = TextConstantValueDefinitionVO(constant["value"])
    else:
        raise InvalidFeedSchemaDocumentError("Неизвестное текстовое определение.")
    fallback = None
    if definition.get("fallback_policy") is not None:
        policy = document(definition["fallback_policy"], {"mode"}, {"locales"})
        fallback = LocaleFallbackPolicyVO(
            LocaleFallbackMode(string(policy["mode"])),
            tuple(
                LocaleCodeVO(string(item))
                for item in array(policy.get("locales", []), 32)
            ),
        )
    constructor = {
        "string": ShortTextNodeDataVO,
        "text": LongTextNodeDataVO,
        "rich_text": RichTextNodeDataVO,
    }[kind]
    field_type = constructor(
        value_definition=value_definition,
        locale=(
            LocaleCodeVO(string(definition["locale"]))
            if definition.get("locale") is not None
            else None
        ),
        fallback_policy=fallback,
        constraints=TextConstraintsVO(
            required=constraints.get("required", False),
            min_length=constraints.get("min_length"),
            max_length=constraints.get("max_length"),
        ),
        transforms=transforms,
    )
    return field_type


def write_text(definition: ShortTextNodeDataVO | LongTextNodeDataVO) -> JsonObject:
    """Представляет настройки ноды для JSON-документа."""
    settings: JsonObject = {"kind": definition.kind.value}
    settings["locale"] = (
        definition.locale.value if definition.locale is not None else None
    )
    settings["fallback_policy"] = (
        {
            "mode": definition.fallback_policy.mode.value,
            "locales": [locale.value for locale in definition.fallback_policy.locales],
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
    settings["transforms"] = [
        transform_document(item) for item in definition.transforms
    ]
    return settings
