from src.modules.feed_builder.application.feed.port.schema_locales import (
    SchemaLocalesPort,
)
from src.modules.feed_builder.domain.feed.error import InvalidFieldDefinitionError
from src.modules.feed_builder.domain.feed.expression.calculation_policy import (
    PriceCalculationSemanticPolicy,
)
from src.modules.feed_builder.domain.feed.expression.error import (
    CalculationDefinitionError,
)
from src.modules.feed_builder.domain.feed.field_node.category.value_object.data import (
    CategoryNodeDataVO,
)
from src.modules.feed_builder.domain.feed.field_node.long_text.value_object.data import (
    LongTextNodeDataVO,
)
from src.modules.feed_builder.domain.feed.field_node.money.value_object.data import (
    MoneyNodeDataVO,
)
from src.modules.feed_builder.domain.feed.field_node.short_text.value_object.data import (
    ShortTextNodeDataVO,
)
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO


async def validate_saved_graph(
    schema: FeedSchemaVO, previous: FeedSchemaVO, locales: SchemaLocalesPort
) -> None:
    """Проверяет внешние ссылки и новые денежные формулы рабочего графа."""
    previous_fields = {field.id: field.type_definition for field in previous.fields}
    needed: list[tuple[int, str]] = []
    for index, field in enumerate(schema.fields):
        settings = field.type_definition
        original = previous_fields.get(field.id)
        if isinstance(settings, MoneyNodeDataVO):
            calculation = settings.value_definition.calculation
            previous_calculation = (
                original.value_definition.calculation
                if isinstance(original, MoneyNodeDataVO)
                else None
            )
            if calculation is not None and calculation != previous_calculation:
                try:
                    PriceCalculationSemanticPolicy.ensure_valid(calculation)
                except CalculationDefinitionError as exc:
                    exc.path = (
                        "definition",
                        "fields",
                        index,
                        "data",
                        "value",
                        "calculation",
                        *exc.path,
                    )
                    raise
        if isinstance(settings, CategoryNodeDataVO) and any(
            node.catalog_id is not None for node in settings.nodes
        ):
            needed.append((index, settings.locale.value))
        if isinstance(settings, (ShortTextNodeDataVO, LongTextNodeDataVO)):
            if settings.locale is not None:
                needed.append((index, settings.locale.value))
            if settings.fallback_policy is not None:
                needed.extend(
                    (index, locale.value) for locale in settings.fallback_policy.locales
                )

    if needed:
        available = {item.code for item in await locales.list_available()}
        for index, code in needed:
            if code not in available:
                raise InvalidFieldDefinitionError(
                    "Локаль недоступна в справочнике.",
                    path=("definition", "fields", index, "data", "locale"),
                )
