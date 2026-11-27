from src.modules.feed_builder.domain.feed.field_node.category.value_object.data import (
    CategoryNodeDataVO,
)
from src.modules.feed_builder.domain.feed.enum.catalog_source_path import (
    CatalogSourcePath,
)
from src.modules.feed_builder.domain.feed.field_node.boolean.value_object.data import (
    BooleanNodeDataVO,
)
from src.modules.feed_builder.domain.feed.field_node.integer.value_object.data import (
    IntegerNodeDataVO,
)
from src.modules.feed_builder.domain.feed.enum.field_value_type import FieldValueType
from src.modules.feed_builder.domain.feed.error import InvalidFieldDefinitionError
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.domain.feed.field_node.money.value_object.data import (
    MoneyNodeDataVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_value_definition import (
    MoneyValueDefinitionVO,
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
        if path is CatalogSourcePath.STOCK_QUANTITY:
            return (FieldValueType.INTEGER,)
        if path is CatalogSourcePath.IN_STOCK:
            return (FieldValueType.BOOLEAN,)
        if path is CatalogSourcePath.DESCRIPTION_HTML:
            return (FieldValueType.RICH_TEXT,)
        return (FieldValueType.STRING, FieldValueType.TEXT)

    @staticmethod
    def requires_locale(path: CatalogSourcePath) -> bool:
        """Отмечает локализованный контент, в отличие от SKU и суммы."""
        return path in (
            CatalogSourcePath.TITLE,
            CatalogSourcePath.DESCRIPTION,
            CatalogSourcePath.DESCRIPTION_HTML,
        )

    @classmethod
    def ensure_valid(cls, schema: FeedSchemaVO) -> None:
        """Отклоняет несовместимый тип и языковые настройки прямого источника."""
        for index, field in enumerate(schema.fields):
            definition = field.type_definition
            if isinstance(definition, CategoryNodeDataVO):
                continue
            value = definition.value_definition
            source = (
                value.source
                if isinstance(value, (MoneyValueDefinitionVO, SourceValueDefinitionVO))
                else None
            )
            if source is None:
                continue
            path = ("definition", "fields", index, "data")
            if definition.kind not in cls.allowed_kinds(source.path):
                raise InvalidFieldDefinitionError(
                    "Источник несовместим с типом поля.",
                    path=path + ("value", "source"),
                )
            if not isinstance(
                definition, (MoneyNodeDataVO, IntegerNodeDataVO, BooleanNodeDataVO)
            ):
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
