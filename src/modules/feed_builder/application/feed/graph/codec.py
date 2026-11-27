from collections.abc import Callable
from decimal import InvalidOperation

from src.modules.feed_builder.application.feed.graph.category_trees import (
    category_tree_document,
    decode_category_trees,
)
from src.modules.feed_builder.application.feed.graph.error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.application.feed.graph.json_values import array, document
from src.modules.feed_builder.application.feed.graph.versioned_node import (
    decode_versioned_node,
    versioned_node_document,
)
from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.domain.feed.limits import MAX_FIELDS
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO


def decode_schema(
    value: object,
    *,
    previous_schema: FeedSchemaVO | None = None,
    clean_html: Callable[[str], str] | None = None,
) -> FeedSchemaVO:
    """Восстанавливает плоские ноды и деревья графа версии 2."""
    graph = document(value, {"schema_format_version", "fields"}, {"categoryTrees"})
    version = graph["schema_format_version"]
    if type(version) is not int or version != 2:
        raise InvalidFeedSchemaDocumentError(
            "Поддерживается только граф версии 2.",
            path=("definition", "schema_format_version"),
        )
    try:
        category_trees = decode_category_trees(
            graph.get("categoryTrees", []), previous_schema
        )
        trees = {tree.id: tree for tree in category_trees}
        if len(trees) != len(category_trees):
            raise InvalidFeedSchemaDocumentError("Дерево категорий указано дважды.")
        fields = tuple(
            decode_versioned_node(
                item,
                ("definition", "fields", index),
                trees,
                clean_html=clean_html,
            )
            for index, item in enumerate(array(graph["fields"], MAX_FIELDS))
        )
        return FeedSchemaVO(fields, category_trees=category_trees)
    except (ValueError, TypeError, KeyError, InvalidOperation) as exc:
        raise InvalidFeedSchemaDocumentError("Некорректное определение Feed.") from exc


def schema_document(value: FeedSchemaVO) -> JsonObject:
    """Сериализует упорядоченные поля и деревья графа версии 2."""
    return {
        "schema_format_version": value.schema_format_version,
        "fields": [versioned_node_document(item) for item in value.fields],
        "categoryTrees": [
            category_tree_document(tree) for tree in value.category_trees
        ],
    }
