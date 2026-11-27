from src.modules.feed_builder.domain.feed.field_node.category.value_object.data import (
    CategoryNodeDataVO,
)
from src.modules.feed_builder.domain.feed.entity.field_node import FieldNodeDefinition
from src.modules.feed_builder.domain.feed.error import (
    DuplicateExportNameError,
    DuplicateFieldIdentifierError,
    DuplicateFieldKeyError,
    InvalidFeedValueError,
)
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.domain.feed.value_object.field_id import FieldIdVO
from src.modules.feed_builder.domain.feed.value_object.field_key import FieldKeyVO
from src.modules.feed_builder.domain.feed.value_object.export_name import ExportNameVO


class FeedSchemaStructurePolicy:
    """Проверяет целостность графа в Feed и снимке экспорта."""

    @staticmethod
    def validate(schema: FeedSchemaVO) -> FeedSchemaVO:
        """Возвращает проверенный снимок без повторов ID, ключей и экспортных имён."""
        if not isinstance(schema, FeedSchemaVO):
            raise InvalidFeedValueError("Нужен FeedSchemaVO.")
        trees = {tree.id: tree.settings for tree in schema.category_trees}
        if len(trees) != len(schema.category_trees):
            raise InvalidFeedValueError("Дерево категорий повторяется в графе.")
        identifiers: set[FieldIdVO] = set()
        keys: set[FieldKeyVO] = set()
        export_names: set[ExportNameVO] = set()
        containers: set[tuple[str, ExportNameVO]] = set()
        restored_fields: list[FieldNodeDefinition] = []
        for index, definition in enumerate(schema.fields):
            definition = FieldNodeDefinition.restore(
                identifier=definition.id,
                key=definition.key,
                label=definition.label,
                type_definition=definition.type_definition,
                export=definition.export,
                ai_instruction=definition.ai_instruction,
                category_tree_id=definition.category_tree_id,
            )
            if definition.id in identifiers:
                raise DuplicateFieldIdentifierError(
                    "Field ID повторяется в Feed.",
                    path=("schema", "fields", index, "id"),
                )
            if definition.key in keys:
                raise DuplicateFieldKeyError(
                    "Ключ поля повторяется в Feed.",
                    path=("schema", "fields", index, "key"),
                )
            if isinstance(definition.type_definition, CategoryNodeDataVO):
                if trees.get(definition.category_tree_id) != definition.type_definition:
                    raise InvalidFeedValueError(
                        "Нода категории ссылается на неизвестное дерево.",
                        path=("schema", "fields", index, "data", "treeId"),
                    )
            export = definition.export
            if definition.type_definition.has_publication_output(export):
                output = export.name
                if output in export_names:
                    raise DuplicateExportNameError(
                        "Экспортное имя повторяется в Feed.",
                        path=("schema", "fields", index, "export", "name"),
                    )
                export_names.add(output)
            if export.enabled and export.document is not None:
                container = (export.document.parent, export.document.container)
                if (
                    container in containers
                    or export.document.parent == "SHOP"
                    and export.document.container.value
                    in ("name", "company", "currencies", "offers")
                ):
                    raise DuplicateExportNameError(
                        "Имя контейнера XML уже занято.",
                        path=("schema", "fields", index, "export", "document"),
                    )
                containers.add(container)
            identifiers.add(definition.id)
            keys.add(definition.key)
            restored_fields.append(definition)
        return FeedSchemaVO(
            tuple(restored_fields), category_trees=schema.category_trees
        )
