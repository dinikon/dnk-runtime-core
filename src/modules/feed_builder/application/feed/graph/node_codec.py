from src.modules.feed_builder.domain.feed.category.value_object.tree import (
    FeedCategoryTreeVO,
)
from src.modules.feed_builder.application.feed.graph.registry import node_codec
from decimal import InvalidOperation
from src.modules.feed_builder.domain.feed.field_node.category.value_object.data import (
    CategoryNodeDataVO,
)
from src.modules.feed_builder.domain.feed.value_object.document_field_export import (
    DocumentFieldExportVO,
)
from src.modules.feed_builder.domain.feed.enum.xml_field_placement import (
    XmlFieldPlacement,
)
from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.shared.domain.domain_error import DomainError
from src.modules.feed_builder.application.feed.graph.error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.domain.feed.entity.field_node import FieldNodeDefinition
from src.modules.feed_builder.domain.feed.value_object.field_id import FieldIdVO
from src.modules.feed_builder.domain.feed.value_object.field_key import FieldKeyVO
from src.modules.feed_builder.domain.feed.value_object.field_label import FieldLabelVO
from src.modules.feed_builder.domain.feed.value_object.field_export_settings import (
    FieldExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.export_name import ExportNameVO
from src.modules.feed_builder.application.feed.graph.json_values import document, string


def decode_field(
    value: object,
    previous: CategoryNodeDataVO | None = None,
    *,
    tree: FeedCategoryTreeVO | None = None,
) -> FieldNodeDefinition:
    """Восстанавливает поле через явную фабрику и собственные проверки VO."""
    data = document(value, {"id", "key", "label", "type_definition", "export"}, {"ai"})
    raw_type = data["type_definition"]
    if not isinstance(raw_type, dict):
        raise InvalidFeedSchemaDocumentError("Нужен объект настроек типа.")
    kind = raw_type.get("kind")
    codec = node_codec(kind)
    field_type = tree.settings if tree is not None else codec.read(raw_type, previous)
    export = document(
        data["export"],
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
            node.get("parent", "ROOT"),
            node.get("layout", "FLAT"),
            ExportNameVO(string(node.get("parent_attribute", "parentId"))),
        )
    publication = (
        document(export["publication"], {"value_key"}, {"required"})
        if export.get("publication") is not None
        else None
    )
    ai = document(data.get("ai", {"instruction": None}), {"instruction"})
    return FieldNodeDefinition.restore(
        identifier=FieldIdVO.from_value(string(data["id"])),
        key=FieldKeyVO(string(data["key"])),
        label=FieldLabelVO(string(data["label"])),
        type_definition=field_type,
        export=FieldExportSettingsVO(
            ExportNameVO(string(export["name"])),
            export["enabled"],
            XmlFieldPlacement(export.get("xml_placement", XmlFieldPlacement.ELEMENT)),
            xml_document,
            ExportNameVO(string(publication["value_key"])) if publication else None,
            publication.get("required", False) if publication else False,
        ),
        ai_instruction=ai["instruction"],
        category_tree_id=tree.id if tree is not None else None,
    )


def decode_field_at(
    value: object,
    index: int,
    previous: CategoryNodeDataVO | None = None,
    *,
    tree: FeedCategoryTreeVO | None = None,
) -> FieldNodeDefinition:
    """Дополняет ошибку фабрики адресом поля без потери предметного исключения."""
    try:
        return decode_field(value, previous, tree=tree)
    except DomainError as exc:
        from src.modules.feed_builder.domain.error import FeedBuilderDomainError

        if isinstance(exc, FeedBuilderDomainError):
            exc.path = ("definition", "root", "fields", index) + exc.path
            raise
        raise InvalidFeedSchemaDocumentError(
            str(exc), path=("definition", "root", "fields", index)
        ) from exc
    except (
        InvalidFeedSchemaDocumentError,
        ValueError,
        TypeError,
        KeyError,
        InvalidOperation,
    ) as exc:
        raise InvalidFeedSchemaDocumentError(
            str(exc), path=("definition", "root", "fields", index)
        ) from exc


def field_export_document(value: FieldExportSettingsVO) -> JsonObject:
    """Передаёт общие параметры экспорта ноды в обеих версиях схемы."""
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


def field_document(value: FieldNodeDefinition) -> JsonObject:
    """Сериализует поле для определения версии 1."""
    definition = value.type_definition
    return {
        "id": str(value.id.uuid),
        "key": value.key.value,
        "label": value.label.value,
        "type_definition": node_codec(definition.kind.value).write(definition),
        "export": field_export_document(value.export),
        "ai": {"instruction": value.ai_instruction},
    }
