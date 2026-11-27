from decimal import InvalidOperation
from uuid import UUID

from src.modules.feed_builder.domain.error import FeedBuilderDomainError
from src.modules.feed_builder.application.feed.graph.error import (
    InvalidFeedSchemaDocumentError,
)
from src.modules.feed_builder.application.feed.graph.category_codec import (
    category_field_document,
    decode_category_field,
)
from src.modules.feed_builder.application.feed.graph.json_values import (
    document,
    string,
)
from src.modules.feed_builder.application.feed.graph.input import CategoryTreeInput
from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.domain.feed.category.value_object.tree import (
    FeedCategoryTreeVO,
)
from src.modules.shared.domain.domain_error import DomainError
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO


def read_category_tree_input(
    value: object, path: tuple[str | int, ...]
) -> CategoryTreeInput:
    """Проверяет оболочку сохранённого дерева V2."""
    try:
        tree = document(value, {"id", "data"})
        settings = tree["data"]
        if not isinstance(settings, dict):
            raise InvalidFeedSchemaDocumentError(
                "Нужны данные дерева категорий.", path=("data",)
            )
        return CategoryTreeInput(string(tree["id"]), settings)
    except InvalidFeedSchemaDocumentError as exc:
        raise InvalidFeedSchemaDocumentError(str(exc), path=(*path, *exc.path)) from exc


def decode_category_trees(
    inputs: tuple[CategoryTreeInput, ...], previous: FeedSchemaVO | None
) -> tuple[FeedCategoryTreeVO, ...]:
    """Восстанавливает деревья и сохраняет ранее назначенные экспортные ID."""
    known = (
        {tree.id: tree.settings for tree in previous.category_trees} if previous else {}
    )
    trees = []
    for index, item in enumerate(inputs):
        path = ("definition", "categoryTrees", index)
        try:
            identifier = UUID(item.id)
        except ValueError as exc:
            raise InvalidFeedSchemaDocumentError(
                "Некорректный ID дерева категорий.", path=(*path, "id")
            ) from exc
        path = (*path, "data")
        try:
            tree = decode_category_field(
                {**item.data, "kind": "category"}, known.get(identifier)
            )
        except FeedBuilderDomainError as exc:
            exc.path = (*path, *exc.path)
            raise
        except InvalidFeedSchemaDocumentError as exc:
            raise InvalidFeedSchemaDocumentError(
                str(exc), path=(*path, *exc.path)
            ) from exc
        except (DomainError, ValueError, TypeError, KeyError, InvalidOperation) as exc:
            raise InvalidFeedSchemaDocumentError(str(exc), path=path) from exc
        trees.append(FeedCategoryTreeVO(identifier, tree))
    return tuple(trees)


def category_tree_document(tree: FeedCategoryTreeVO) -> JsonObject:
    """Представляет локальное дерево отдельно от ссылки в Offer."""
    settings = category_field_document(tree.settings)
    data = {key: value for key, value in settings.items() if key != "kind"}
    return {"id": str(tree.id), "data": data}
