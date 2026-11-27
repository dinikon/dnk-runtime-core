from src.modules.feed_builder.application.feed.graph.category_trees import (
    category_tree_document,
    decode_category_trees,
)
from collections.abc import Callable
from decimal import InvalidOperation
from src.modules.feed_builder.domain.feed.field_node.category.value_object.data import (
    CategoryNodeDataVO,
)
from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.domain.feed.limits import MAX_FIELDS
from src.modules.shared.domain.domain_error import DomainError
from src.modules.feed_builder.application.feed.graph.error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.application.feed.graph.json_values import array, document
from src.modules.feed_builder.application.feed.graph.node_codec import (
    decode_field_at,
    field_document,
)
from src.modules.feed_builder.application.feed.graph.v1_category import (
    decode_inline_categories,
)
from src.modules.feed_builder.application.feed.graph.versioned_node import (
    decode_versioned_node,
    versioned_node_document,
)


def decode_schema(
    value: object,
    *,
    previous_schema: FeedSchemaVO | None = None,
    clean_html: Callable[[str], str] | None = None,
) -> FeedSchemaVO:
    """Собирает схему полей и читает ранее сохранённые определения категорий."""
    try:
        previous = {
            str(field.id.uuid): field.type_definition
            for field in (previous_schema.fields if previous_schema else ())
            if isinstance(field.type_definition, CategoryNodeDataVO)
        }
        if (
            isinstance(value, dict)
            and type(value.get("schema_format_version")) is int
            and value["schema_format_version"] == 2
        ):
            graph = document(
                value, {"schema_format_version", "fields"}, {"categoryTrees"}
            )
            category_trees = decode_category_trees(
                graph.get("categoryTrees", []), previous_schema
            )
            trees = {tree.id: tree for tree in category_trees}
            if len(trees) != len(category_trees):
                raise InvalidFeedSchemaDocumentError("Дерево категорий указано дважды.")
            fields = tuple(
                decode_versioned_node(
                    item,
                    index,
                    trees,
                    clean_html=clean_html,
                )
                for index, item in enumerate(array(graph["fields"], MAX_FIELDS))
            )
            return FeedSchemaVO(fields, 2, category_trees)

        data = document(value, {"schema_format_version", "root"}, {"categories"})
        root = document(data["root"], {"key", "kind", "fields"})
        if (
            root["key"] != "publication"
            or root["kind"] != "object"
            or data["schema_format_version"] != 1
        ):
            raise InvalidFeedSchemaDocumentError("Неизвестный корень документа схемы.")
        fields = [
            decode_field_at(
                item,
                index,
                previous.get(item.get("id")) if isinstance(item, dict) else None,
            )
            for index, item in enumerate(array(root["fields"], MAX_FIELDS))
        ]
        legacy = decode_inline_categories(data.get("categories"), fields)
        if legacy is not None:
            fields.append(legacy)
        return FeedSchemaVO(tuple(fields), data["schema_format_version"])
    except (InvalidFeedSchemaDocumentError, DomainError):
        raise
    except (ValueError, TypeError, KeyError, InvalidOperation) as exc:
        raise InvalidFeedSchemaDocumentError("Некорректное определение Feed.") from exc


def schema_document(value: FeedSchemaVO) -> JsonObject:
    """Возвращает порядок и описание полей в рабочей схеме."""
    if value.schema_format_version == 2:
        return {
            "schema_format_version": 2,
            "fields": [versioned_node_document(item) for item in value.fields],
            "categoryTrees": [
                category_tree_document(tree) for tree in value.category_trees
            ],
        }
    return {
        "schema_format_version": value.schema_format_version,
        "root": {
            "key": "publication",
            "kind": "object",
            "fields": [field_document(item) for item in value.fields],
        },
    }
