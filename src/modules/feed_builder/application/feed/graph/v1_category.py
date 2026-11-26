from typing import cast
from uuid import NAMESPACE_URL, uuid5
from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.domain.feed.entity.field_node import FieldNodeDefinition
from src.modules.feed_builder.application.feed.graph.json_values import array, document
from src.modules.feed_builder.application.feed.graph.node_codec import decode_field


def decode_inline_categories(
    value: object, fields: list[FieldNodeDefinition]
) -> FieldNodeDefinition | None:
    """Читает ранее сохранённый блок как поле, включая снимки ожидающих задач."""
    if value is None:
        return None
    block = document(
        value,
        {"version", "enabled", "profile", "locale", "nodes", "rules", "fallback"},
        {
            "catalog_priority",
            "next_export_id",
            "fallback_id",
            "attribute_types",
            "element_types",
            "name_transforms",
        },
    )
    profile = block["profile"]
    prop = [
        {
            "key": "id",
            "kind": "string",
            "required": True,
            "xml": {"placement": "ATTRIBUTE"},
        },
        {
            "key": "name",
            "kind": "text",
            "required": True,
            "source": "CATALOG_NAME",
            "xml": {
                "placement": (
                    "ELEMENT"
                    if profile == "GENERIC" and block.get("element_types")
                    else "TEXT"
                )
            },
        },
    ]
    attributes = (
        block.get("attribute_types", {})
        if profile == "GENERIC"
        else (
            {"portal_id": "string", "portal_url": "string"}
            if profile == "PROM"
            else {"rz_id": "string"}
        )
    )
    elements = block.get("element_types", {}) if profile == "GENERIC" else {}
    used_property_keys = {"id", "name"} | attributes.keys() | elements.keys()
    property_keys: dict[tuple[str, str], str] = {}
    for placement, definitions in (("ATTRIBUTE", attributes), ("ELEMENT", elements)):
        for name, kind in definitions.items():
            key = name
            if name in ("id", "name") or (
                placement == "ELEMENT" and name in attributes
            ):
                key = f"legacy_{len(prop)}"
                while key in used_property_keys:
                    key += "_"
                used_property_keys.add(key)
            property_keys[placement, name] = key
            prop.append(
                {
                    "key": key,
                    "kind": "integer" if kind == "number" else kind,
                    "xml": {"placement": placement, "name": name},
                }
            )

    nodes = []
    for item in array(block["nodes"], 1000):
        node = cast(JsonObject, item)
        values = {"id": node["export_id"]} if node.get("export_id") is not None else {}
        if node.get("name") is not None:
            values["name"] = node["name"]
        if profile == "GENERIC":
            for placement, section in (
                ("ATTRIBUTE", "attributes"),
                ("ELEMENT", "elements"),
            ):
                properties = cast(JsonObject, node.get(section, {}))
                values.update(
                    {
                        property_keys[placement, name]: value
                        for name, value in properties.items()
                    }
                )
        else:
            values.update(
                {key: node[key] for key in attributes if node.get(key) is not None}
            )
        nodes.append(
            {
                key: node[key]
                for key in ("id", "parent_id", "catalog_id", "inherit_parent")
                if key in node
            }
            | {"values": values}
        )

    key = "feed_category"
    used = {field.key.value for field in fields}
    while key in used:
        key += "_"
    return decode_field(
        {
            "id": str(uuid5(NAMESPACE_URL, "feed-builder/category/" + key)),
            "key": key,
            "label": "Категория",
            "export": {
                "name": "categoryId",
                "enabled": block["enabled"],
                "publication": {"value_key": "id", "required": profile != "GENERIC"},
                "document": {
                    "parent": "ROOT" if profile == "GENERIC" else "SHOP",
                    "container": "categories",
                    "item": "category",
                },
            },
            "type_definition": {
                "kind": "category",
                "locale": block["locale"],
                "name_transforms": block.get("name_transforms", []),
                "object_schema": {"id_key": "id", "label_key": "name", "fields": prop},
                "value": {
                    key: block[key]
                    for key in (
                        "rules",
                        "fallback",
                        "fallback_id",
                        "catalog_priority",
                        "next_export_id",
                    )
                    if key in block
                }
                | {"kind": "INLINE", "nodes": nodes},
            },
        }
    )
