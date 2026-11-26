from uuid import UUID

from src.modules.feed_builder.domain.error import FeedBuilderDomainError
from src.modules.feed_builder.application.feed.graph.error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.domain.feed.field_node.category.value_object.data import (
    CategoryNodeDataVO,
)
from src.modules.feed_builder.application.feed.graph.category_codec import (
    category_field_document,
    decode_category_field,
)
from src.modules.feed_builder.application.feed.graph.json_values import (
    array,
    document,
    string,
)
from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.domain.feed.category.value_object.tree import (
    FeedCategoryTreeVO,
)
from src.modules.feed_builder.domain.feed.limits import MAX_FIELDS
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO


def decode_category_trees(
    value: object, previous: FeedSchemaVO | None
) -> tuple[FeedCategoryTreeVO, ...]:
    """Восстанавливает деревья отдельного раздела и сохраняет назначенные ID."""
    known = (
        {tree.id: tree.settings for tree in previous.category_trees} if previous else {}
    )
    if previous is not None and previous.schema_format_version == 1:
        known.update(
            (field.id.uuid, field.type_definition)
            for field in previous.fields
            if isinstance(field.type_definition, CategoryNodeDataVO)
        )
    trees = []
    for index, item in enumerate(array(value, MAX_FIELDS)):
        data = document(item, {"id", "data"})
        identifier = UUID(string(data["id"]))
        settings = data["data"]
        if not isinstance(settings, dict):
            raise InvalidFeedSchemaDocumentError("Нужны данные дерева категорий.")
        try:
            tree = decode_category_field(
                {**settings, "kind": "category"}, known.get(identifier)
            )
        except (FeedBuilderDomainError, InvalidFeedSchemaDocumentError) as exc:
            exc.path = ("definition", "categoryTrees", index, "data", *exc.path)
            raise
        trees.append(FeedCategoryTreeVO(identifier, tree))
    return tuple(trees)


def category_tree_document(tree: FeedCategoryTreeVO) -> JsonObject:
    """Представляет локальное дерево отдельно от ссылки в Offer."""
    settings = category_field_document(tree.settings)
    data = {key: value for key, value in settings.items() if key != "kind"}
    return {"id": str(tree.id), "data": data}
