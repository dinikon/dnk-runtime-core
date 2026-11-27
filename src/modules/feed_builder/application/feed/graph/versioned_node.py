from collections.abc import Callable, Mapping
from decimal import InvalidOperation
from uuid import UUID

from src.modules.feed_builder.domain.feed.category.value_object.tree import (
    FeedCategoryTreeVO,
)
from src.modules.feed_builder.domain.feed.enum.field_value_type import FieldValueType
from src.modules.feed_builder.domain.error import FeedBuilderDomainError
from src.modules.feed_builder.application.feed.graph.input import FieldNodeInput
from src.modules.feed_builder.application.feed.graph.forms import node_forms
from src.modules.feed_builder.application.feed.graph.json_values import (
    document,
    integer,
    string,
)
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


def read_field_node_input(value: object, path: tuple[str | int, ...]) -> FieldNodeInput:
    """Разбирает общие свойства сохранённой ноды независимо от типа данных."""
    try:
        node = document(
            value,
            {"id", "key", "name", "typeId", "typeVersion", "scope", "data", "export"},
            {"forms", "aiInstruction"},
        )
        if node["scope"] != "offer":
            raise InvalidFeedSchemaDocumentError(
                "Некорректная область ноды.", path=("scope",)
            )
        settings, export = node["data"], node["export"]
        if not isinstance(settings, dict):
            raise InvalidFeedSchemaDocumentError(
                "Нужен объект данных ноды.", path=("data",)
            )
        if not isinstance(export, dict):
            raise InvalidFeedSchemaDocumentError(
                "Нужен объект настроек экспорта.", path=("export",)
            )
        instruction = node.get("aiInstruction")
        return FieldNodeInput(
            id=string(node["id"]),
            key=string(node["key"]),
            name=string(node["name"]),
            type_id=string(node["typeId"]),
            type_version=integer(node["typeVersion"], ("typeVersion",)),
            data=settings,
            export=export,
            ai_instruction=string(instruction) if instruction is not None else None,
        )
    except InvalidFeedSchemaDocumentError as exc:
        raise InvalidFeedSchemaDocumentError(str(exc), path=(*path, *exc.path)) from exc


def decode_versioned_node(
    node: FieldNodeInput,
    path: tuple[str | int, ...],
    trees: Mapping[UUID, FeedCategoryTreeVO],
    *,
    clean_html: Callable[[str], str] | None = None,
) -> FieldNodeDefinition:
    """Сопоставляет входную ноду с зарегистрированным типом и строит Entity."""
    section = path
    try:
        codec = versioned_node_codec(node.type_id, node.type_version)
        section = (*path, "data")
        settings = node.data
        tree = None
        if codec.kind is FieldValueType.CATEGORY:
            reference = document(settings, {"source", "treeId"})
            if reference["source"] != "feed":
                raise InvalidFeedSchemaDocumentError(
                    "Нужен источник категорий фида.", path=("source",)
                )
            section = (*path, "data", "treeId")
            tree = trees.get(UUID(string(reference["treeId"])))
            if tree is None:
                raise InvalidFeedSchemaDocumentError(
                    "Нода категории ссылается на неизвестное дерево."
                )
            field_type = tree.settings
        else:
            if "kind" in settings:
                raise InvalidFeedSchemaDocumentError(
                    "Нужен объект данных зарегистрированного типа.", path=("kind",)
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
                settings = {
                    **settings,
                    "value": {**constant, "value": clean_html(html)},
                }
            field_type = codec.read({**settings, "kind": codec.kind.value}, None)

        section = (*path, "id")
        identifier = FieldIdVO.from_value(node.id)
        section = (*path, "key")
        key = FieldKeyVO(node.key)
        section = (*path, "name")
        label = FieldLabelVO(node.name)
        section = (*path, "export")
        export = decode_field_export(node.export)
        section = path
        return FieldNodeDefinition.restore(
            identifier=identifier,
            key=key,
            label=label,
            type_definition=field_type,
            export=export,
            ai_instruction=node.ai_instruction,
            category_tree_id=tree.id if tree is not None else None,
        )
    except FeedBuilderDomainError as exc:
        suffix = exc.path
        if suffix[:1] == ("type_definition",):
            suffix = ("data", *suffix[1:])
        parent = path if suffix[:1] in (("data",), ("export",)) else section
        exc.path = (*parent, *suffix)
        raise
    except InvalidFeedSchemaDocumentError as exc:
        raise InvalidFeedSchemaDocumentError(
            str(exc), path=(*section, *exc.path)
        ) from exc
    except (DomainError, ValueError, TypeError, KeyError, InvalidOperation) as exc:
        raise InvalidFeedSchemaDocumentError(str(exc), path=section) from exc


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
