from src.modules.feed_builder.domain.feed.value_object.category_field_type import (
    CategoryFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.entity.field_definition import FieldDefinition
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
    """Проверяет состав определения в фабриках Feed и снимка FeedGeneration."""

    @staticmethod
    def validate(schema: FeedSchemaVO) -> FeedSchemaVO:
        """Возвращает проверенный снимок без повторов ID, ключей и экспортных имён."""
        if not isinstance(schema, FeedSchemaVO):
            raise InvalidFeedValueError("Нужен FeedSchemaVO.")
        identifiers: set[FieldIdVO] = set()
        keys: set[FieldKeyVO] = set()
        export_names: set[ExportNameVO] = set()
        containers: set[tuple[str, ExportNameVO]] = set()
        restored_fields: list[FieldDefinition] = []
        for index, definition in enumerate(schema.fields):
            definition = FieldDefinition.restore(
                identifier=definition.id,
                key=definition.key,
                label=definition.label,
                type_definition=definition.type_definition,
                export=definition.export,
                ai_instruction=definition.ai_instruction,
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
            export = definition.export
            if (
                not isinstance(definition.type_definition, CategoryFieldTypeVO)
                or export.publication_key is not None
            ):
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
        return FeedSchemaVO(tuple(restored_fields), schema.schema_format_version)
