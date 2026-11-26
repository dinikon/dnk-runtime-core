from collections.abc import Mapping
from uuid import UUID

from src.modules.feed_builder.domain.feed.category.value_object.tree import (
    FeedCategoryTreeVO,
)
from src.modules.feed_builder.domain.feed.enum.field_value_type import FieldValueType
from src.modules.feed_builder.domain.error import FeedBuilderDomainError
from src.modules.feed_builder.application.feed.graph.forms import node_forms
from src.modules.feed_builder.application.feed.graph.json_values import document, string
from src.modules.feed_builder.application.feed.graph.node_codec import (
    decode_field_at,
    field_export_document,
)
from src.modules.feed_builder.application.feed.graph.registry import (
    node_codec,
    versioned_node_codec,
)
from src.modules.feed_builder.application.feed.graph.error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.domain.feed.entity.field_node import FieldNodeDefinition


def decode_versioned_node(
    value: object, index: int, trees: Mapping[UUID, FeedCategoryTreeVO]
) -> FieldNodeDefinition:
    """Сопоставляет ноду с зарегистрированным типом и проверяет её данные."""
    path = ("definition", "fields", index)
    try:
        data = document(
            value,
            {"id", "key", "name", "typeId", "typeVersion", "scope", "data", "export"},
            {"forms", "aiInstruction"},
        )
        if type(data["typeVersion"]) is not int or data["scope"] != "offer":
            raise InvalidFeedSchemaDocumentError(
                "Некорректная версия или область ноды."
            )
        codec = versioned_node_codec(string(data["typeId"]), data["typeVersion"])
        settings = data["data"]
        tree = None
        if codec.kind is FieldValueType.CATEGORY:
            reference = document(settings, {"source", "treeId"})
            tree_id = UUID(string(reference["treeId"]))
            tree = trees.get(tree_id)
            if reference["source"] != "feed" or tree is None:
                raise InvalidFeedSchemaDocumentError(
                    "Нода категории ссылается на неизвестное дерево."
                )
            settings = {}
        if not isinstance(settings, dict) or "kind" in settings:
            raise InvalidFeedSchemaDocumentError(
                "Нужен объект данных зарегистрированного типа."
            )
    except (InvalidFeedSchemaDocumentError, ValueError) as exc:
        raise InvalidFeedSchemaDocumentError(str(exc), path=path) from exc
    try:
        return decode_field_at(
            {
                "id": data["id"],
                "key": data["key"],
                "label": data["name"],
                "type_definition": {**settings, "kind": codec.kind.value},
                "export": data["export"],
                "ai": {"instruction": data.get("aiInstruction")},
            },
            index,
            tree=tree,
        )
    except FeedBuilderDomainError as exc:
        tail = exc.path[4:]
        if tail[:1] == ("type_definition",):
            tail = ("data", *tail[1:])
        exc.path = (*path, *tail)
        raise
    except InvalidFeedSchemaDocumentError as exc:
        raise InvalidFeedSchemaDocumentError(str(exc), path=path) from exc


def versioned_node_document(field: FieldNodeDefinition) -> JsonObject:
    """Возвращает данные и серверную форму одной ноды плоского графа."""
    codec = node_codec(field.type_definition.kind.value)
    if field.category_tree_id is not None:
        data: JsonObject = {"source": "feed", "treeId": str(field.category_tree_id)}
    else:
        settings = codec.write(field.type_definition)
        data = {key: item for key, item in settings.items() if key != "kind"}
    return {
        "id": str(field.id.uuid),
        "key": field.key.value,
        "name": field.label.value,
        "typeId": codec.type_id,
        "typeVersion": codec.version,
        "scope": "offer",
        "forms": node_forms(codec),
        "data": data,
        "export": field_export_document(field.export),
        "aiInstruction": field.ai_instruction,
    }
