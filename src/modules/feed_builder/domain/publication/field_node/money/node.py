from src.modules.feed_builder.domain.feed.expression.error import (
    CalculationDefinitionError,
)
from src.modules.feed_builder.domain.feed.expression.evaluation import (
    MoneyFieldCalculator,
)
from src.modules.feed_builder.domain.feed.entity.field_node import FieldNodeDefinition
from src.modules.feed_builder.domain.feed.enum.money_value_mode import MoneyValueMode
from src.modules.feed_builder.domain.feed.field_node.money.value_object.data import (
    MoneyNodeDataVO,
)
from src.modules.feed_builder.domain.feed.value_object.price_amount import PriceAmountVO
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


class MoneyNode(FieldNode[MoneyNodeDataVO]):
    """Вычисляет сумму по источнику или правилам публикации."""

    data_type = MoneyNodeDataVO

    def resolve_value(
        self,
        field: FieldNodeDefinition,
        settings: MoneyNodeDataVO,
        snapshot: PublicationCatalogSnapshotVO,
        override: FieldOverrideVO | None,
    ) -> ResolvedField:
        """Переиспользует денежный вычислитель и его финальные преобразования."""
        mode = settings.value_definition.mode
        manual = override is not None or mode is MoneyValueMode.MANUAL
        origin = (
            "MANUAL"
            if manual
            else "CALCULATED" if mode is MoneyValueMode.CALCULATED else "INHERITED"
        )
        missing = (
            (override is None or override.value is None)
            if manual
            else mode is MoneyValueMode.SOURCE and snapshot.inputs.regular is None
        )
        if missing:
            if settings.constraints.required:
                return invalid_value(
                    field, origin, "REQUIRED_VALUE_MISSING", "Требуется значение поля."
                )
            return ResolvedField(field.id.uuid, None, origin)
        if override is not None and not isinstance(override.value, PriceAmountVO):
            return invalid_value(
                field, origin, "INVALID_FIELD_VALUE", "Ожидается денежная сумма."
            )
        try:
            result = MoneyFieldCalculator.calculate(
                field,
                snapshot.inputs,
                manual_amount=override.value if override is not None else None,
            )
        except CalculationDefinitionError as exc:
            return ResolvedField(
                field.id.uuid,
                None,
                origin,
                issues=(FieldIssue(field.id.uuid, exc.code, str(exc), exc.path),),
            )
        return ResolvedField(
            field.id.uuid,
            result.value,
            origin,
            issues=tuple(
                FieldIssue(
                    field.id.uuid, issue.code, issue.message, issue.path, issue.rule_id
                )
                for issue in result.issues
            ),
        )
