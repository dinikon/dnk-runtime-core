from collections.abc import Callable, Mapping
from decimal import InvalidOperation
from uuid import UUID

from src.modules.feed_builder.domain.feed.category.value_object.tree import (
    FeedCategoryTreeVO,
)
from src.modules.feed_builder.domain.feed.enum.field_value_type import FieldValueType
from src.modules.feed_builder.domain.error import FeedBuilderDomainError
from src.modules.feed_builder.application.feed.graph.forms import node_forms
from src.modules.feed_builder.application.feed.graph.json_values import document, string
from src.modules.feed_builder.application.feed.graph.node_codec import (
    decode_field_export,
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
from src.modules.feed_builder.domain.feed.value_object.field_id import FieldIdVO
from src.modules.feed_builder.domain.feed.value_object.field_key import FieldKeyVO
from src.modules.feed_builder.domain.feed.value_object.field_label import FieldLabelVO
from src.modules.shared.domain.domain_error import DomainError
from src.modules.feed_builder.domain.feed.field_node.value_validation import (
    valid_text_characters,
)


def decode_versioned_node(
    value: object,
    path: tuple[str | int, ...],
    trees: Mapping[UUID, FeedCategoryTreeVO],
    *,
    clean_html: Callable[[str], str] | None = None,
) -> FieldNodeDefinition:
    """Сопоставляет ноду с зарегистрированным типом и проверяет её данные."""
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
        constant = settings.get("value")
        if (
            codec.kind is FieldValueType.RICH_TEXT
            and clean_html is not None
            and isinstance(constant, dict)
            and constant.get("kind") == "CONSTANT"
            and isinstance(html := constant.get("value"), str)
            and valid_text_characters(html, multiline=True)
        ):
            settings = {**settings, "value": {**constant, "value": clean_html(html)}}
        field_type = (
            tree.settings
            if tree is not None
            else codec.read({**settings, "kind": codec.kind.value}, None)
        )
        return FieldNodeDefinition.restore(
            identifier=FieldIdVO.from_value(string(data["id"])),
            key=FieldKeyVO(string(data["key"])),
            label=FieldLabelVO(string(data["name"])),
            type_definition=field_type,
            export=decode_field_export(data["export"]),
            ai_instruction=data.get("aiInstruction"),
            category_tree_id=tree.id if tree is not None else None,
        )
    except FeedBuilderDomainError as exc:
        suffix = exc.path
        if suffix[:1] == ("type_definition",):
            suffix = ("data", *suffix[1:])
        exc.path = (*path, *suffix)
        raise
    except (
        InvalidFeedSchemaDocumentError,
        DomainError,
        ValueError,
        TypeError,
        KeyError,
        InvalidOperation,
    ) as exc:
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
