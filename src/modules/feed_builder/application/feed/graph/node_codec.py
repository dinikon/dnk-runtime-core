from src.modules.feed_builder.application.feed.graph.json_values import (
    boolean,
    choice,
    document,
    string,
)
from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.domain.feed.enum.xml_field_placement import (
    XmlFieldPlacement,
)
from src.modules.feed_builder.domain.feed.value_object.document_field_export import (
    DocumentFieldExportVO,
)
from src.modules.feed_builder.domain.feed.value_object.export_name import ExportNameVO
from src.modules.feed_builder.domain.feed.value_object.field_export_settings import (
    FieldExportSettingsVO,
)


def decode_field_export(value: object) -> FieldExportSettingsVO:
    """Восстанавливает общие параметры экспорта ноды из JSON."""
    export = document(
        value,
        {"name", "enabled"},
        {"xml_placement", "document", "publication"},
    )
    xml_document = None
    if export.get("document") is not None:
        node = document(
            export["document"],
            {"container", "item"},
            {"parent", "layout", "parent_attribute"},
        )
        xml_document = DocumentFieldExportVO(
            ExportNameVO(string(node["container"])),
            ExportNameVO(string(node["item"])),
            choice(
                node.get("parent", "ROOT"), ("ROOT", "SHOP"), ("document", "parent")
            ),
            choice(
                node.get("layout", "FLAT"), ("FLAT", "NESTED"), ("document", "layout")
            ),
            ExportNameVO(string(node.get("parent_attribute", "parentId"))),
        )
    publication = (
        document(export["publication"], {"value_key"}, {"required"})
        if export.get("publication") is not None
        else None
    )
    return FieldExportSettingsVO(
        ExportNameVO(string(export["name"])),
        boolean(export["enabled"], ("enabled",)),
        XmlFieldPlacement(export.get("xml_placement", XmlFieldPlacement.ELEMENT)),
        xml_document,
        ExportNameVO(string(publication["value_key"])) if publication else None,
        (
            boolean(publication.get("required", False), ("publication", "required"))
            if publication
            else False
        ),
    )


def field_export_document(value: FieldExportSettingsVO) -> JsonObject:
    """Передаёт общие параметры экспорта ноды графа."""
    export: JsonObject = {
        "name": value.name.value,
        "enabled": value.enabled,
    }
    if value.xml_placement is XmlFieldPlacement.ATTRIBUTE:
        export["xml_placement"] = value.xml_placement.value
    if value.document is not None:
        layout = value.document
        export["document"] = {
            "container": layout.container.value,
            "item": layout.item.value,
            "parent": layout.parent,
            "layout": layout.layout,
            "parent_attribute": layout.parent_attribute.value,
        }
    if value.publication_key is not None:
        export["publication"] = {
            "value_key": value.publication_key.value,
            "required": value.required,
        }
    return export
