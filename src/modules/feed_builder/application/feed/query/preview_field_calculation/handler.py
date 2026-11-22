import hashlib
import json
from src.modules.feed_builder.application.feed.query.preview_field_calculation.query import (
    PreviewFieldCalculationQuery,
)
from src.modules.feed_builder.application.feed.query.preview_field_calculation.dto import (
    PreviewFieldCalculationResultDTO,
    CalculationPreviewIssueDTO,
    CalculationPreviewStepDTO,
)
from src.modules.feed_builder.application.feed.port.query_repository import (
    FeedQueryRepositoryProtocol,
)
from src.modules.feed_builder.application.feed.port.calculation_product import (
    CalculationProductReaderProtocol,
)
from src.modules.feed_builder.application.feed.schema_definition import (
    decode_schema,
    decode_field_at,
)
from src.modules.feed_builder.application.feed.schema_document import field_document
from src.modules.feed_builder.domain.feed.calculation.parameters import ENGINE_VERSION
from src.modules.feed_builder.domain.feed.calculation.error import (
    CalculationDefinitionError,
)
from src.modules.feed_builder.domain.feed.calculation.evaluator import (
    MoneyFieldCalculator,
)
from src.modules.feed_builder.domain.feed.value_object.money_field_type import (
    MoneyFieldTypeVO,
)
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.domain.feed.policy.schema_structure import (
    FeedSchemaStructurePolicy,
)
from src.modules.feed_builder.domain.feed.policy.schema_sources import (
    FeedSchemaSourcePolicy,
)
from src.modules.feed_builder.domain.feed.policy.calculation_semantics import (
    PriceCalculationSemanticPolicy,
)
from src.modules.feed_builder.domain.feed.value_object.feed_version import FeedVersionVO
from src.modules.feed_builder.domain.feed.error import (
    FeedNotFoundError,
    FeedVersionConflictError,
    FeedArchivedError,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class PreviewFieldCalculationHandler:
    """Собирает read-side снимки, вызывает Domain и не сохраняет агрегаты."""

    def __init__(
        self,
        repository: FeedQueryRepositoryProtocol,
        products: CalculationProductReaderProtocol,
        clock: ClockPort,
    ) -> None:
        """Принимает только необходимые порты текущего tenant."""
        self._repository, self._products, self._clock = repository, products, clock

    async def execute(
        self, query: PreviewFieldCalculationQuery
    ) -> PreviewFieldCalculationResultDTO:
        """Проверяет версию и весь AST до чтения реальных входов, затем объясняет выбранную ветвь."""
        expected = FeedVersionVO(query.expected_version)
        current = await self._repository.get_schema(query.feed_id)
        if current is None:
            raise FeedNotFoundError("Feed не найден.")
        if current.version != expected.value:
            raise FeedVersionConflictError("Feed уже изменён.")
        if current.status == "ARCHIVED":
            raise FeedArchivedError("Архивный Feed доступен только для просмотра.")
        schema = decode_schema(current.definition)
        original = next(
            (field for field in schema.fields if field.id.uuid == query.field_id), None
        )
        if query.definition_override is None:
            if original is None:
                raise FeedNotFoundError("Поле Feed не найдено.")
            field = original
        else:
            field = decode_field_at(query.definition_override, 0)
            if field.id.uuid != query.field_id:
                raise CalculationDefinitionError(
                    "FIELD_ID_MISMATCH",
                    "Определение должно принадлежать проверяемому полю.",
                )
        fields = tuple(field if old.id == field.id else old for old in schema.fields)
        if original is None:
            fields += (field,)
        FeedSchemaStructurePolicy.validate(FeedSchemaVO(fields))
        FeedSchemaSourcePolicy.ensure_valid(FeedSchemaVO((field,)))
        if not isinstance(field.type_definition, MoneyFieldTypeVO):
            raise CalculationDefinitionError(
                "INVALID_EXPRESSION_TYPE", "Предпросмотр цены требует MONEY-поле."
            )
        calculation = field.type_definition.value_definition.calculation
        if calculation is not None:
            PriceCalculationSemanticPolicy.ensure_valid(calculation)
        as_of = self._clock.now()
        product = await self._products.read(
            query.catalog_item_id, query.catalog_variant_id, as_of
        )
        result = MoneyFieldCalculator.calculate(field, product.inputs)
        definition_hash = hashlib.sha256(
            json.dumps(
                field_document(field),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode()
        ).hexdigest()
        return PreviewFieldCalculationResultDTO(
            feed_id=current.feed_id,
            version=current.version,
            field_id=field.id.uuid,
            definition_hash=definition_hash,
            catalog_item_id=product.item_id,
            catalog_variant_id=product.variant_id,
            selected_product_id=product.selected_id,
            product_kind=product.kind,
            sku=product.inputs.sku,
            source_revision=product.revision,
            as_of=as_of,
            valid_until=product.valid_until,
            calculation_engine_version=ENGINE_VERSION,
            validation_status="VALID" if result.value is not None else "INVALID",
            amount=(
                format(result.value.amount.amount, "f")
                if result.value is not None
                else None
            ),
            currency=(
                result.value.currency.value
                if result.value is not None and result.value.currency is not None
                else None
            ),
            selected_rule_id=result.selected_rule_id,
            used_default=result.used_default,
            steps=tuple(
                CalculationPreviewStepDTO(
                    step.path, step.operation, step.value, step.rule_id
                )
                for step in result.steps
            ),
            parameters=result.parameters,
            issues=tuple(
                CalculationPreviewIssueDTO(
                    issue.code, issue.message, field.id.uuid, issue.rule_id, issue.path
                )
                for issue in result.issues
            ),
        )
