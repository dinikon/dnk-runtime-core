from src.modules.feed_builder.domain.feed.enum.catalog_source_path import (
    CatalogSourcePath,
)
from src.modules.feed_builder.domain.feed.enum.field_value_type import FieldValueType
from src.modules.feed_builder.domain.feed.error import InvalidFieldDefinitionError
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.domain.feed.value_object.money_field_type import (
    MoneyFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.source_value_definition import (
    SourceValueDefinitionVO,
)


class FeedSchemaSourcePolicy:
    """Проверяет совместимость закрытых прямых источников без чтения Catalog."""

    @staticmethod
    def allowed_kinds(path: CatalogSourcePath) -> tuple[FieldValueType, ...]:
        """Возвращает типы результата зарегистрированного логического пути."""
        if path is CatalogSourcePath.REGULAR_PRICE:
            return (FieldValueType.MONEY,)
        return (FieldValueType.STRING, FieldValueType.TEXT)

    @staticmethod
    def requires_locale(path: CatalogSourcePath) -> bool:
        """Отмечает локализованный контент, в отличие от SKU и суммы."""
        return path in (CatalogSourcePath.TITLE, CatalogSourcePath.DESCRIPTION)

    @classmethod
    def ensure_valid(cls, schema: FeedSchemaVO) -> None:
        """Отклоняет несовместимый тип и языковые настройки прямого источника."""
        for index, field in enumerate(schema.fields):
            definition = field.type_definition
            source = (
                definition.value_definition.source
                if isinstance(definition, MoneyFieldTypeVO)
                or isinstance(definition.value_definition, SourceValueDefinitionVO)
                else None
            )
            if source is None:
                continue
            path = ("definition", "root", "fields", index, "type_definition")
            if definition.kind not in cls.allowed_kinds(source.path):
                raise InvalidFieldDefinitionError(
                    "Источник несовместим с типом поля.",
                    path=path + ("value", "source"),
                )
            if not isinstance(definition, MoneyFieldTypeVO):
                if cls.requires_locale(source.path) and definition.locale is None:
                    raise InvalidFieldDefinitionError(
                        "Для источника текста нужна локаль.", path=path + ("locale",)
                    )
                if not cls.requires_locale(source.path) and (
                    definition.locale is not None
                    or definition.fallback_policy is not None
                ):
                    raise InvalidFieldDefinitionError(
                        "Языконезависимый источник не принимает локаль или fallback.",
                        path=path + ("locale",),
                    )
