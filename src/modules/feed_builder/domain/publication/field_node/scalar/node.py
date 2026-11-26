from src.modules.feed_builder.domain.feed.types import ScalarFieldType
from src.modules.feed_builder.domain.feed.expression.value_object.boolean_calculation import (
    BooleanCalculationVO,
)
from src.modules.feed_builder.domain.feed.field_node.boolean.value_object.data import (
    BooleanNodeDataVO,
)
from src.modules.feed_builder.domain.feed.value_object.constant_value_definition import (
    ConstantValueDefinitionVO,
)
from src.modules.feed_builder.domain.feed.field_node.integer.value_object.data import (
    IntegerNodeDataVO,
)
from src.modules.feed_builder.domain.feed.expression.evaluation import calculate_boolean
from src.modules.feed_builder.domain.feed.entity.field_node import FieldNodeDefinition
from src.modules.feed_builder.domain.feed.enum.catalog_source_path import (
    CatalogSourcePath,
)
from src.modules.feed_builder.domain.feed.value_object.source_value_definition import (
    SourceValueDefinitionVO,
)
from src.modules.feed_builder.domain.publication.value_object.field_override import (
    FieldOverrideVO,
)
from src.modules.feed_builder.domain.publication.value_object.publication_catalog_snapshot import (
    PublicationCatalogSnapshotVO,
)
from src.modules.feed_builder.domain.publication.field_node.base import (
    FieldNode,
    invalid_value,
)
from src.modules.feed_builder.domain.publication.field_node.result import (
    FieldIssue,
    ResolvedField,
)


class ScalarNode(FieldNode[ScalarFieldType]):
    """Вычисляет числовые и логические значения публикации."""

    data_type = (IntegerNodeDataVO, BooleanNodeDataVO)

    def resolve_value(
        self,
        field: FieldNodeDefinition,
        settings: ScalarFieldType,
        snapshot: PublicationCatalogSnapshotVO,
        override: FieldOverrideVO | None,
    ) -> ResolvedField:
        """Разрешает числовые и логические поля без подмены нуля и false."""
        definition = settings.value_definition
        if override is not None:
            value, origin = override.value, "MANUAL"
        elif isinstance(definition, ConstantValueDefinitionVO):
            value, origin = definition.value, "CONSTANT"
        elif isinstance(definition, SourceValueDefinitionVO):
            value = (
                snapshot.inputs.stock_quantity
                if definition.source.path is CatalogSourcePath.STOCK_QUANTITY
                else snapshot.inputs.in_stock
            )
            origin = "INHERITED"
        elif isinstance(definition, BooleanCalculationVO):
            result = calculate_boolean(definition, snapshot.inputs)
            if result.issues:
                return ResolvedField(
                    field.id.uuid,
                    None,
                    "CALCULATED",
                    issues=tuple(
                        FieldIssue(field.id.uuid, issue.code, issue.message, issue.path)
                        for issue in result.issues
                    ),
                )
            value, origin = result.value, "CALCULATED"
        else:
            value, origin = None, "MANUAL"
        if value is None:
            if settings.required:
                return invalid_value(
                    field, origin, "REQUIRED_VALUE_MISSING", "Требуется значение поля."
                )
        elif isinstance(settings, IntegerNodeDataVO) and not settings.accepts(value):
            return invalid_value(
                field,
                origin,
                "INVALID_INTEGER_VALUE",
                "Нужно целое число в допустимых границах поля.",
            )
        elif isinstance(settings, BooleanNodeDataVO) and type(value) is not bool:
            return invalid_value(
                field, origin, "INVALID_BOOLEAN_VALUE", "Ожидается true или false."
            )
        return ResolvedField(field.id.uuid, value, origin)
