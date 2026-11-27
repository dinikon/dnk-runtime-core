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
    tree_positions = {
        tree.id: index for index, tree in enumerate(schema.category_trees)
    }
    checked_trees: set[int] = set()
    needed: list[tuple[tuple[str | int, ...], str]] = []
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
        if (
            isinstance(settings, CategoryNodeDataVO)
            and field.category_tree_id is not None
        ):
            tree_index = tree_positions.get(field.category_tree_id)
            if tree_index is not None and tree_index not in checked_trees:
                checked_trees.add(tree_index)
                if any(node.catalog_id is not None for node in settings.nodes):
                    needed.append(
                        (
                            (
                                "definition",
                                "categoryTrees",
                                tree_index,
                                "data",
                                "locale",
                            ),
                            settings.locale.value,
                        )
                    )
        if isinstance(settings, (ShortTextNodeDataVO, LongTextNodeDataVO)):
            path = ("definition", "fields", index, "data")
            if settings.locale is not None:
                needed.append(((*path, "locale"), settings.locale.value))
            if settings.fallback_policy is not None:
                needed.extend(
                    ((*path, "fallback_policy", "locales", position), locale.value)
                    for position, locale in enumerate(settings.fallback_policy.locales)
                )

    if needed:
        available = {item.code for item in await locales.list_available()}
        for path, code in needed:
            if code not in available:
                raise InvalidFieldDefinitionError(
                    "Локаль недоступна в справочнике.",
                    path=path,
                )
