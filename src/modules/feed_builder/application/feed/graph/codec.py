from collections.abc import Callable

from src.modules.feed_builder.application.feed.graph.category_trees import (
    category_tree_document,
    decode_category_trees,
    read_category_tree_input,
)
from src.modules.feed_builder.application.feed.graph.error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.application.feed.graph.input import FeedGraphInput
from src.modules.feed_builder.application.feed.graph.json_values import array, document
from src.modules.feed_builder.application.feed.graph.versioned_node import (
    decode_versioned_node,
    read_field_node_input,
    versioned_node_document,
)
from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.domain.feed.limits import MAX_FIELDS
from src.modules.feed_builder.domain.feed.policy.schema_structure import (
    FeedSchemaStructurePolicy,
)
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO


def read_graph_input(value: object) -> FeedGraphInput:
    """Проверяет оболочку сохранённого V2 и типизирует её содержимое."""
    graph = document(value, {"schema_format_version", "fields"}, {"categoryTrees"})
    version = graph["schema_format_version"]
    if type(version) is not int or version != 2:
        raise InvalidFeedSchemaDocumentError(
            "Поддерживается только граф версии 2.",
            path=("definition", "schema_format_version"),
        )
    return FeedGraphInput(
        fields=tuple(
            read_field_node_input(item, ("definition", "fields", index))
            for index, item in enumerate(array(graph["fields"], MAX_FIELDS))
        ),
        category_trees=tuple(
            read_category_tree_input(item, ("definition", "categoryTrees", index))
            for index, item in enumerate(
                array(graph.get("categoryTrees", []), MAX_FIELDS)
            )
        ),
    )


def decode_schema(value: object) -> FeedSchemaVO:
    """Восстанавливает сохранённый V2 через тот же набор кодеков нод."""
    schema = build_schema(read_graph_input(value))
    FeedSchemaStructurePolicy.index_category_trees(schema.category_trees)
    return schema


def build_schema(
    graph: FeedGraphInput,
    *,
    previous_schema: FeedSchemaVO | None = None,
    clean_html: Callable[[str], str] | None = None,
) -> FeedSchemaVO:
    """Собирает доменный граф из входных нод и дерева каждой ссылки."""
    category_trees = decode_category_trees(graph.category_trees, previous_schema)
    trees = {tree.id: tree for tree in category_trees}
    fields = tuple(
        decode_versioned_node(
            item,
            ("definition", "fields", index),
            trees,
            clean_html=clean_html,
        )
        for index, item in enumerate(graph.fields)
    )
    return FeedSchemaVO(fields, category_trees=category_trees)


def schema_document(value: FeedSchemaVO) -> JsonObject:
    """Сериализует упорядоченные поля и деревья графа версии 2."""
    return {
        "schema_format_version": value.schema_format_version,
        "fields": [versioned_node_document(item) for item in value.fields],
        "categoryTrees": [
            category_tree_document(tree) for tree in value.category_trees
        ],
    }
