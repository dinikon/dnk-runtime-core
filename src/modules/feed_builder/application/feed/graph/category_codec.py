from typing import cast
from uuid import UUID
from src.modules.feed_builder.domain.feed.field_node.category.value_object.data import (
    CategoryNodeDataVO,
)
from src.modules.feed_builder.domain.feed.value_object.category_property import (
    CategoryPropertyVO,
)
from src.modules.feed_builder.domain.feed.value_object.category_node import (
    CategoryNodeVO,
)
from src.modules.feed_builder.domain.feed.value_object.category_rule import (
    CategoryRuleVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.boolean_calculation import (
    BooleanCalculationVO,
)
from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.domain.feed.limits import MAX_TRANSFORMS
from src.modules.feed_builder.application.feed.graph.error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.domain.feed.value_object.export_name import ExportNameVO
from src.modules.feed_builder.domain.feed.value_object.locale_code import LocaleCodeVO
from src.modules.feed_builder.application.feed.graph.json_values import (
    array,
    document,
    string,
)
from src.modules.feed_builder.application.feed.graph.expression_codec import (
    ExpressionReader,
    node_document,
)
from src.modules.feed_builder.application.feed.graph.field_settings_codec import (
    decode_transform,
    transform_document,
)
from src.modules.feed_builder.domain.error import FeedBuilderDomainError


def decode_category_field(
    value: object, previous: CategoryNodeDataVO | None
) -> CategoryNodeDataVO:
    """Восстанавливает записи категории и назначает свободные ID в пределах поля."""
    data = document(
        value, {"kind", "object_schema", "value"}, {"locale", "name_transforms"}
    )
    shape = document(data["object_schema"], {"id_key", "label_key", "fields"})
    props = []
    for item in array(shape["fields"], 64):
        prop = document(item, {"key", "kind"}, {"required", "xml", "source"})
        key = string(prop["key"])
        xml = document(prop.get("xml", {}), set(), {"placement", "name"})
        props.append(
            CategoryPropertyVO(
                ExportNameVO(key),
                prop["kind"],
                prop.get("required", False),
                xml.get("placement", "NONE"),
                ExportNameVO(string(xml.get("name") or key)),
                prop.get("source"),
            )
        )
    block = document(
        data["value"],
        {"kind", "nodes", "rules", "fallback"},
        {"fallback_id", "catalog_priority", "next_export_id"},
    )
    if block["kind"] != "INLINE":
        raise InvalidFeedSchemaDocumentError("Неизвестный источник записей категории.")
    key = string(shape["id_key"])
    id_kind = next((prop.kind for prop in props if prop.key.value == key), None)
    nodes = [
        document(item, {"id", "values"}, {"parent_id", "catalog_id", "inherit_parent"})
        for item in array(block["nodes"], 1000)
    ]
    raw_values = []
    for item in nodes:
        if not isinstance(item["values"], dict):
            raise InvalidFeedSchemaDocumentError(
                "Значения записи должны быть объектом."
            )
        raw_values.append(cast(JsonObject, item["values"]).copy())
    old_ids = (
        {node.id: dict(node.values)[previous.id_key] for node in previous.nodes}
        if previous
        else {}
    )
    occupied = {str(values[key]) for values in raw_values if key in values} | {
        str(identifier) for identifier in old_ids.values()
    }
    next_id = previous.next_export_id if previous else block.get("next_export_id", 1)
    if type(next_id) is not int or not 1 <= next_id <= 2**53 - 1:
        raise InvalidFeedSchemaDocumentError("Некорректный счётчик ID категорий.")

    def optional_id(raw: object) -> UUID | None:
        """Декодирует необязательную ссылку дерева."""
        return UUID(string(raw)) if raw is not None else None

    parsed = []
    for item, values in zip(nodes, raw_values, strict=True):
        node_id = UUID(string(item["id"]))
        identifier = values.get(key)
        if node_id in old_ids:
            old_id = old_ids[node_id]
            if identifier is not None and (
                type(identifier) is not type(old_id) or identifier != old_id
            ):
                raise InvalidFeedSchemaDocumentError(
                    "ID сохранённой категории изменить нельзя."
                )
            identifier = old_id
        elif identifier is None:
            while str(next_id) in occupied:
                next_id += 1
            identifier = next_id if id_kind == "integer" else str(next_id)
            occupied.add(str(identifier))
            next_id += 1
        elif str(identifier) in {str(old) for old in old_ids.values()}:
            raise InvalidFeedSchemaDocumentError(
                "ID уже использован другой записью поля."
            )
        value_text = str(identifier)
        if value_text.isascii() and value_text.isdecimal() and len(value_text) <= 16:
            number = int(value_text)
            if number < 2**53 - 1 and str(number) == value_text:
                next_id = max(next_id, number + 1)
        values[key] = identifier
        parsed.append(
            CategoryNodeVO(
                node_id,
                tuple(values.items()),
                optional_id(item.get("parent_id")),
                optional_id(item.get("catalog_id")),
                item.get("inherit_parent", False),
            )
        )
    rules = []
    for index, item in enumerate(array(block["rules"], 100)):
        try:
            rule = document(
                item, {"id", "target_id", "condition", "label"}, {"include_descendants"}
            )
            rules.append(
                CategoryRuleVO(
                    UUID(string(rule["id"])),
                    UUID(string(rule["target_id"])),
                    BooleanCalculationVO(ExpressionReader().node(rule["condition"])),
                    string(rule["label"]),
                    rule.get("include_descendants", False),
                )
            )
        except (FeedBuilderDomainError, InvalidFeedSchemaDocumentError) as exc:
            exc.path = ("value", "rules", index, *exc.path)
            raise
    return CategoryNodeDataVO(
        tuple(props),
        key,
        string(shape["label_key"]),
        LocaleCodeVO(string(data.get("locale", "uk"))),
        tuple(parsed),
        tuple(rules),
        block["fallback"],
        optional_id(block.get("fallback_id")),
        tuple(
            UUID(string(item))
            for item in array(block.get("catalog_priority", []), 1000)
        ),
        next_id,
        tuple(
            decode_transform(item)
            for item in array(data.get("name_transforms", []), MAX_TRANSFORMS)
        ),
    )


def category_field_document(value: CategoryNodeDataVO) -> JsonObject:
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
