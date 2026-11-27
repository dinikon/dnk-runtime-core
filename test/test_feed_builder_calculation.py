"""Чистая семантика, исполнение и read-only сценарий предпросмотра цены."""

from dataclasses import replace
from decimal import Decimal, localcontext
from unittest import TestCase, IsolatedAsyncioTestCase
from unittest.mock import Mock, AsyncMock
from uuid import uuid4, UUID

from src.modules.feed_builder.domain.feed.entity.field_node import FieldNodeDefinition
from src.modules.feed_builder.domain.feed.types import Expression
from test.test_feed_builder_domain import money_field, rule, feed, NOW
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.feed_builder.domain.feed.expression.value_object.calculation_inputs import (
    CalculationInputsVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.price_calculation import (
    PriceCalculationVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.parameter_reference import (
    ParameterReferenceVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.decimal_literal import (
    DecimalLiteralVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.arithmetic_expression import (
    ArithmeticExpressionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.function_expression import (
    FunctionExpressionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.presence_condition import (
    PresenceConditionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.logical_condition import (
    LogicalConditionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.comparison_condition import (
    ComparisonConditionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.scalar_literal import (
    ScalarLiteralVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.collection_literal import (
    CollectionLiteralVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_constraints import (
    MoneyConstraintsVO,
)
from src.modules.feed_builder.domain.feed.value_object.transform_definition import (
    TransformDefinitionVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_ceil_step_parameters import (
    MoneyCeilStepParametersVO,
)
from src.modules.feed_builder.domain.feed.expression.enum.arithmetic_operator import (
    ArithmeticOperator as A,
)
from src.modules.feed_builder.domain.feed.expression.enum.price_function import (
    PriceFunction as F,
)
from src.modules.feed_builder.domain.feed.expression.enum.comparison_operator import (
    ComparisonOperator as C,
)
from src.modules.feed_builder.domain.feed.expression.enum.presence_operator import (
    PresenceOperator as P,
)
from src.modules.feed_builder.domain.feed.expression.enum.logical_operator import (
    LogicalOperator as L,
)
from src.modules.feed_builder.domain.feed.expression.enum.literal_value_type import (
    LiteralValueType as V,
)
from src.modules.feed_builder.domain.feed.enum.transform_operation import (
    TransformOperation as T,
)
from src.modules.feed_builder.domain.feed.expression.evaluation import (
    MoneyFieldCalculator,
    ceil_step,
)
from src.modules.feed_builder.domain.feed.expression.error import (
    CalculationDefinitionError,
)
from src.modules.feed_builder.domain.feed.expression.calculation_policy import (
    PriceCalculationSemanticPolicy,
)
from src.modules.feed_builder.application.feed.query.preview_field_calculation.handler import (
    PreviewFieldCalculationHandler,
)
from src.modules.feed_builder.application.feed.query.preview_field_calculation.query import (
    PreviewFieldCalculationQuery,
)
from src.modules.feed_builder.application.feed.query.get_feed_schema.dto import (
    FeedSchemaDetailsDTO,
)
from src.modules.feed_builder.application.feed.port.calculation_product import (
    CalculationProductSnapshot,
)
from src.modules.feed_builder.application.feed.graph.codec import schema_document
from src.modules.feed_builder.application.feed.graph.versioned_node import (
    read_field_node_input,
    versioned_node_document,
)
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.domain.feed.error import (
    FeedArchivedError,
    FeedVersionConflictError,
)


def number(value: str) -> DecimalLiteralVO:
    """Создаёт точную константу."""
    return DecimalLiteralVO(Decimal(value))


def binary(operator: A, left: Expression, right: Expression) -> ArithmeticExpressionVO:
    """Собирает типизированную бинарную арифметику фикстуры."""
    return ArithmeticExpressionVO(operator, left=left, right=right)


def inputs(
    sale: str | None = "900", regular: str | None = "1000"
) -> CalculationInputsVO:
    """Передаёт реальные по типам суммы выбранной позиции без валюты."""
    return CalculationInputsVO(
        EntityIdVO(uuid4()),
        "SKU-WHITE",
        Decimal(regular) if regular is not None else None,
        Decimal(sale) if sale is not None else None,
        Decimal(sale or regular) if sale is not None or regular is not None else None,
    )


def calculation_field() -> FieldNodeDefinition:
    """Описывает IF sale EXISTS, ELSE regular с независимыми коэффициентами."""
    return money_field(
        PriceCalculationVO(
            binary(A.MULTIPLY, ParameterReferenceVO("price.regular"), number("1.15")),
            (
                rule(
                    PresenceConditionVO(P.EXISTS, ParameterReferenceVO("price.sale")),
                    binary(
                        A.MULTIPLY, ParameterReferenceVO("price.sale"), number("1.10")
                    ),
                ),
            ),
        )
    )


class FeedPriceExecutionTests(TestCase):
    """Проверяет финансовый результат, выбранную ветвь и безопасное объяснение."""

    def test_sale_branch_default_and_first_match(self) -> None:
        """Выбирает первое истинное IF либо обязательное ELSE без каскадной наценки."""
        field = calculation_field()
        result = MoneyFieldCalculator.calculate(field, inputs())
        self.assertEqual(result.value.amount.amount, Decimal("990"))
        self.assertEqual(
            result.selected_rule_id,
            field.type_definition.value_definition.calculation.rules[0].id.uuid,
        )
        self.assertFalse(result.used_default)
        self.assertEqual(dict(result.parameters), {"price.sale": "900"})
        default = MoneyFieldCalculator.calculate(field, inputs(sale=None))
        self.assertEqual(default.value.amount.amount, Decimal("1150"))
        self.assertTrue(default.used_default)
        self.assertEqual(dict(default.parameters)["price.sale"], None)
        calculation = field.type_definition.value_definition.calculation
        duplicate = replace(
            calculation,
            rules=calculation.rules
            + (rule(calculation.rules[0].condition, number("1")),),
        )
        self.assertEqual(
            MoneyFieldCalculator.calculate(
                money_field(duplicate), inputs()
            ).value.amount.amount,
            Decimal("990"),
        )

    def test_short_circuit_and_nonselected_division_are_not_executed(self) -> None:
        """Не исполняет ненужные операнды ALL/ANY и невыбранные формулы."""
        bad = binary(A.DIVIDE, number("1"), number("0"))
        condition = LogicalConditionVO(
            L.ALL,
            (
                PresenceConditionVO(P.EXISTS, ParameterReferenceVO("price.sale")),
                ComparisonConditionVO(C.GT, bad, number("0")),
            ),
        )
        field = money_field(PriceCalculationVO(number("7"), (rule(condition, bad),)))
        result = MoneyFieldCalculator.calculate(field, inputs(sale=None))
        self.assertEqual(result.value.amount.amount, Decimal("7"))
        self.assertFalse(any(step.operation == "DIVIDE" for step in result.steps))
        true = ComparisonConditionVO(
            C.EQ, ScalarLiteralVO(V.BOOLEAN, True), ScalarLiteralVO(V.BOOLEAN, True)
        )
        condition = LogicalConditionVO(
            L.ANY, (true, ComparisonConditionVO(C.GT, bad, number("0")))
        )
        self.assertEqual(
            MoneyFieldCalculator.calculate(
                money_field(
                    PriceCalculationVO(number("9"), (rule(condition, number("8")),))
                ),
                inputs(),
            ).value.amount.amount,
            Decimal("8"),
        )

    def test_zero_empty_and_missing_remain_distinct(self) -> None:
        """Сохраняет различие отсутствия, нулевой цены и пустого SKU."""
        field = calculation_field()
        zero = MoneyFieldCalculator.calculate(field, inputs(sale="0"))
        self.assertFalse(zero.used_default)
        self.assertEqual(zero.value.amount.amount, Decimal("0"))
        condition = PresenceConditionVO(P.EXISTS, ParameterReferenceVO("product.sku"))
        field = money_field(
            PriceCalculationVO(number("2"), (rule(condition, number("1")),))
        )
        self.assertEqual(
            MoneyFieldCalculator.calculate(
                field, replace(inputs(), sku="")
            ).value.amount.amount,
            Decimal("1"),
        )
        self.assertEqual(
            MoneyFieldCalculator.calculate(
                field, replace(inputs(), sku=None)
            ).value.amount.amount,
            Decimal("2"),
        )

    def test_selected_formula_or_condition_error_does_not_fall_through(self) -> None:
        """Адресует ошибку выбранной ветви и не переходит скрыто к ELSE."""
        missing = ComparisonConditionVO(
            C.GT, ParameterReferenceVO("price.sale"), number("0")
        )
        result = MoneyFieldCalculator.calculate(
            money_field(
                PriceCalculationVO(number("99"), (rule(missing, number("1")),))
            ),
            inputs(sale=None),
        )
        self.assertEqual(result.issues[0].code, "CALCULATION_PARAMETER_MISSING")
        self.assertIsNone(result.value)
        self.assertFalse(result.used_default)
        self.assertIsNotNone(result.issues[0].rule_id)
        field = money_field(
            PriceCalculationVO(binary(A.DIVIDE, number("1"), number("0")))
        )
        result = MoneyFieldCalculator.calculate(field, inputs())
        self.assertEqual(result.issues[0].code, "DIVISION_BY_ZERO")
        self.assertTrue(result.used_default)
        self.assertEqual(result.issues[0].path, ("default_expression",))

    def test_context_is_fixed_currency_optional_and_rounding_exact(self) -> None:
        """Не зависит от внешнего Decimal context и точно округляет к шагу."""
        field = money_field(
            PriceCalculationVO(binary(A.DIVIDE, number("1"), number("3")))
        )
        field = replace(
            field, type_definition=replace(field.type_definition, currency=None)
        )
        with localcontext() as context:
            context.prec = 3
            result = MoneyFieldCalculator.calculate(field, inputs())
        self.assertEqual(result.value.amount.amount, Decimal("0." + "3" * 40))
        self.assertIsNone(result.value.currency)
        field = replace(
            field,
            type_definition=replace(
                field.type_definition,
                transforms=(
                    TransformDefinitionVO(
                        T.MONEY_CEIL_STEP, MoneyCeilStepParametersVO(Decimal("0.1"))
                    ),
                ),
            ),
        )
        self.assertEqual(
            MoneyFieldCalculator.calculate(field, inputs()).value.amount.amount,
            Decimal("0.4"),
        )
        self.assertEqual(ceil_step(Decimal("590.21"), Decimal("0.1")), Decimal("590.3"))
        self.assertEqual(ceil_step(Decimal("-1.01"), Decimal("0.1")), Decimal("-1.0"))
        self.assertEqual(
            ceil_step(Decimal("9" * 40), Decimal("1E-128")), Decimal("9" * 40)
        )

    def test_range_constraints_and_no_hidden_negative_rejection(self) -> None:
        """Проверяет числовой бюджет и только явно заданные ограничения суммы."""
        field = money_field(
            PriceCalculationVO(binary(A.MULTIPLY, number("1E128"), number("1E128")))
        )
        self.assertEqual(
            MoneyFieldCalculator.calculate(field, inputs()).issues[0].code,
            "NUMERIC_RANGE_EXCEEDED",
        )
        field = money_field(PriceCalculationVO(number("-5")))
        self.assertEqual(
            MoneyFieldCalculator.calculate(field, inputs()).value.amount.amount,
            Decimal("-5"),
        )
        field = replace(
            field,
            type_definition=replace(
                field.type_definition,
                constraints=MoneyConstraintsVO(min_amount=Decimal("0")),
            ),
        )
        self.assertEqual(
            MoneyFieldCalculator.calculate(field, inputs()).issues[0].code,
            "AMOUNT_CONSTRAINT_VIOLATION",
        )

    def test_sku_uuid_membership_functions_and_not(self) -> None:
        """Вычисляет типизированные UUID, функции и логические группы."""
        data = inputs()
        condition = LogicalConditionVO(
            L.ALL,
            (
                ComparisonConditionVO(
                    C.IN,
                    ParameterReferenceVO("product.id"),
                    CollectionLiteralVO(
                        V.UUID, (ScalarLiteralVO(V.UUID, data.product_id),)
                    ),
                ),
                LogicalConditionVO(
                    L.NOT,
                    (
                        PresenceConditionVO(
                            P.IS_MISSING, ParameterReferenceVO("product.sku")
                        ),
                    ),
                ),
            ),
        )
        expression = FunctionExpressionVO(
            F.MAX,
            (
                FunctionExpressionVO(
                    F.ABS, (ArithmeticExpressionVO(A.NEGATE, operand=number("4")),)
                ),
                FunctionExpressionVO(F.MIN, (number("9"), number("8"))),
            ),
        )
        self.assertEqual(
            MoneyFieldCalculator.calculate(
                money_field(
                    PriceCalculationVO(number("0"), (rule(condition, expression),))
                ),
                data,
            ).value.amount.amount,
            Decimal("8"),
        )

    def test_static_types_and_unavailable_parameters_checked_in_all_branches(
        self,
    ) -> None:
        for expression in (
            ParameterReferenceVO("product.category_ids"),
            ParameterReferenceVO("product.unknown"),
            binary(A.ADD, ParameterReferenceVO("product.sku"), number("1")),
        ):
            field = money_field(
                PriceCalculationVO(
                    number("5"),
                    (
                        rule(
                            PresenceConditionVO(
                                P.EXISTS, ParameterReferenceVO("price.sale")
                            ),
                            expression,
                        ),
                    ),
                )
            )
            with self.assertRaises(CalculationDefinitionError):
                MoneyFieldCalculator.calculate(field, inputs(sale=None))
        with self.assertRaises(CalculationDefinitionError):
            PriceCalculationSemanticPolicy.ensure_valid(
                PriceCalculationVO(
                    number("5"),
                    (
                        rule(
                            ComparisonConditionVO(
                                C.IN,
                                ParameterReferenceVO("price.regular"),
                                CollectionLiteralVO(
                                    V.STRING, (ScalarLiteralVO(V.STRING, "100"),)
                                ),
                            ),
                            number("1"),
                        ),
                    ),
                )
            )


class FeedPricePreviewApplicationTests(IsolatedAsyncioTestCase):
    """Проверяет текущую версию Feed, override и отсутствие write-side зависимостей."""

    async def asyncSetUp(self) -> None:
        """Собирает read-only порты и часы без PostgreSQL."""
        self.field = calculation_field()
        self.feed = feed(FeedSchemaVO((self.field,)))
        self.current = FeedSchemaDetailsDTO(
            self.feed.id.uuid, 1, "DRAFT", schema_document(self.feed.schema)
        )
        self.repository = Mock(get_schema=AsyncMock(return_value=self.current))
        self.product = CalculationProductSnapshot(
            uuid4(), None, uuid4(), "simple", 9, None, inputs()
        )
        self.products = Mock(read=AsyncMock(return_value=self.product))
        self.handler = PreviewFieldCalculationHandler(
            self.repository, self.products, Mock(now=lambda: NOW)
        )
        self.query = PreviewFieldCalculationQuery(
            self.feed.id, 1, self.field.id.uuid, self.product.item_id
        )

    async def test_preview_override_and_new_unsaved_field_never_write(self) -> None:
        """Позволяет проверить локальное поле до первого сохранения схемы."""
        result = await self.handler.execute(self.query)
        self.assertEqual(result.amount, "990.00")
        self.assertEqual(result.source_revision, 9)
        self.assertEqual(result.as_of, NOW)
        self.assertEqual(self.current.version, 1)
        new_field = money_field(PriceCalculationVO(number("123.1234567890123456789")))
        from src.modules.feed_builder.domain.feed.value_object.field_key import (
            FieldKeyVO,
        )
        from src.modules.feed_builder.domain.feed.value_object.export_name import (
            ExportNameVO,
        )

        new_field = replace(
            new_field,
            key=FieldKeyVO("preview_price"),
            export=replace(new_field.export, name=ExportNameVO("preview_price")),
        )
        result = await self.handler.execute(
            replace(
                self.query,
                field_id=new_field.id.uuid,
                definition_override=read_field_node_input(
                    versioned_node_document(new_field), ("definition_override",)
                ),
            )
        )
        self.assertEqual(result.amount, "123.1234567890123456789")
        self.assertEqual(result.field_id, new_field.id.uuid)

    async def test_conflicts_archive_and_unknown_override_stop_before_source_read(
        self,
    ) -> None:
        """Не подставляет новую версию и не читает источник после отказа."""
        with self.assertRaises(FeedVersionConflictError):
            await self.handler.execute(replace(self.query, expected_version=2))
        self.repository.get_schema.return_value = replace(
            self.current, status="ARCHIVED"
        )
        with self.assertRaises(FeedArchivedError):
            await self.handler.execute(self.query)
        self.repository.get_schema.return_value = self.current
        bad = versioned_node_document(
            replace(
                money_field(
                    PriceCalculationVO(ParameterReferenceVO("product.category_ids"))
                ),
                id=self.field.id,
            )
        )
        with self.assertRaises(CalculationDefinitionError):
            await self.handler.execute(
                replace(
                    self.query,
                    field_id=UUID(bad["id"]),
                    definition_override=read_field_node_input(
                        bad, ("definition_override",)
                    ),
                )
            )
        self.products.read.assert_not_awaited()
