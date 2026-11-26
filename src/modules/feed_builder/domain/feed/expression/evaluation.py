from decimal import (
    Decimal,
    Context,
    localcontext,
    ROUND_HALF_UP,
    DecimalException,
    Underflow,
)
from uuid import UUID
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.feed_builder.domain.feed.expression.value_object.boolean_calculation import (
    BooleanCalculationVO,
)
from src.modules.feed_builder.domain.feed.expression.error import (
    CalculationExecutionError,
    CalculationDefinitionError,
)
from src.modules.feed_builder.domain.feed.enum.catalog_source_path import (
    CatalogSourcePath,
)
from src.modules.feed_builder.domain.feed.expression.parameters import PRECISION
from src.modules.feed_builder.domain.feed.expression.result import (
    BooleanCalculationResult,
    CalculationStep,
    CalculationIssue,
    PriceCalculationResult,
    TraceValue,
)
from src.modules.feed_builder.domain.feed.expression.calculation_policy import (
    PriceCalculationSemanticPolicy,
)
from src.modules.feed_builder.domain.feed.entity.field_node import FieldNodeDefinition
from src.modules.feed_builder.domain.feed.expression.value_object.calculation_inputs import (
    CalculationInputsVO,
)
from src.modules.feed_builder.domain.feed.value_object.price_value import PriceValueVO
from src.modules.feed_builder.domain.feed.value_object.price_amount import PriceAmountVO
from src.modules.feed_builder.domain.feed.field_node.money.value_object.data import (
    MoneyNodeDataVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.parameter_reference import (
    ParameterReferenceVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.decimal_literal import (
    DecimalLiteralVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.scalar_literal import (
    ScalarLiteralVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.collection_literal import (
    CollectionLiteralVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.arithmetic_expression import (
    ArithmeticExpressionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.function_expression import (
    FunctionExpressionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.comparison_condition import (
    ComparisonConditionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.logical_condition import (
    LogicalConditionVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.presence_condition import (
    PresenceConditionVO,
)
from src.modules.feed_builder.domain.feed.value_object.money_ceil_step_parameters import (
    MoneyCeilStepParametersVO,
)
from src.modules.feed_builder.domain.feed.validation import decimal
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError
from src.modules.feed_builder.domain.feed.limits import MAX_AST_NODES

type RuntimeValue = Decimal | str | bool | EntityIdVO | tuple[
    str | bool | EntityIdVO, ...
]


def trace_value(value: RuntimeValue | None) -> TraceValue:
    """Переводит точные значения в безопасные JSON-примитивы без float."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, EntityIdVO):
        return str(value.uuid)
    if isinstance(value, tuple):
        return tuple(
            str(item.uuid) if isinstance(item, EntityIdVO) else item for item in value
        )
    return value


def ceil_step(amount: Decimal, step: Decimal) -> Decimal:
    """Округляет к шагу точно через целые коэффициенты, включая отрицательные суммы."""

    def parts(value: Decimal) -> tuple[int, int]:
        """Выделяет подписанный коэффициент и степень без ambient Decimal context."""
        data = value.as_tuple()
        coefficient = int("".join(str(d) for d in data.digits))
        return -coefficient if data.sign else coefficient, int(data.exponent)

    amount_int, amount_exp = parts(amount)
    step_int, step_exp = parts(step)
    exponent = min(amount_exp, step_exp)
    numerator = amount_int * 10 ** (amount_exp - exponent)
    denominator = step_int * 10 ** (step_exp - exponent)
    units = -((-numerator) // denominator)
    coefficient = units * step_int
    while coefficient and coefficient % 10 == 0 and step_exp < 128:
        coefficient //= 10
        step_exp += 1
    return Decimal(
        (int(coefficient < 0), tuple(int(d) for d in str(abs(coefficient))), step_exp)
    )


class _Execution:
    """Владеет бюджетом и trace ровно одного вызова чистого вычислителя."""

    def __init__(self, inputs: CalculationInputsVO) -> None:
        """Создаёт локальное состояние, не разделяемое параллельными расчётами."""
        self.inputs = inputs
        self.steps: list[CalculationStep] = []
        self.used: dict[str, TraceValue] = {}
        self.rule_id: UUID | None = None
        self.nodes = 0

    def record(
        self, path: tuple[str | int, ...], operation: str, value: RuntimeValue | None
    ) -> None:
        """Записывает только действительно исполненный шаг."""
        self.steps.append(
            CalculationStep(path, operation, trace_value(value), self.rule_id)
        )

    def parameter(
        self, name: str, path: tuple[str | int, ...], *, allow_missing: bool = False
    ) -> RuntimeValue | None:
        """Регистрирует зависимость, в том числе проверенное отсутствие параметра."""
        value = self.inputs.get(name)
        if isinstance(value, Decimal):
            self.numeric(value, path)
        self.used[name] = trace_value(value)
        if value is None and not allow_missing:
            raise CalculationExecutionError(
                "CALCULATION_PARAMETER_MISSING", "Параметр отсутствует: " + name, path
            )
        return value

    def numeric(self, value: RuntimeValue, path: tuple[str | int, ...]) -> Decimal:
        """Не смешивает bool, строки и суммы при вычислении арифметики."""
        if not isinstance(value, Decimal):
            raise CalculationExecutionError(
                "INVALID_EXPRESSION_TYPE", "Требуется числовая сумма.", path
            )
        try:
            decimal(value, label="Calculation result")
        except InvalidFeedValueError as exc:
            raise CalculationExecutionError(
                "NUMERIC_RANGE_EXCEEDED", "Результат превышает числовой бюджет.", path
            ) from exc
        return value

    def node(self, node: object, path: tuple[str | int, ...]) -> RuntimeValue:
        """Вычисляет закрытый AST с коротким замыканием и конечным бюджетом."""
        self.nodes += 1
        if self.nodes > MAX_AST_NODES:
            raise CalculationExecutionError(
                "CALCULATION_LIMIT_EXCEEDED", "Превышен бюджет исполнения.", path
            )
        try:
            result = self._node(node, path)
            if isinstance(result, Decimal):
                self.numeric(result, path)
        except DecimalException as exc:
            raise CalculationExecutionError(
                "NUMERIC_RANGE_EXCEEDED",
                "Результат не помещается в числовой диапазон.",
                path,
            ) from exc
        operation = (
            node.operator.value
            if isinstance(
                node,
                (
                    ArithmeticExpressionVO,
                    ComparisonConditionVO,
                    LogicalConditionVO,
                    PresenceConditionVO,
                ),
            )
            else (
                node.function.value
                if isinstance(node, FunctionExpressionVO)
                else (
                    node.parameter
                    if isinstance(node, ParameterReferenceVO)
                    else (
                        node.kind
                        if isinstance(
                            node,
                            (DecimalLiteralVO, ScalarLiteralVO, CollectionLiteralVO),
                        )
                        else "invalid"
                    )
                )
            )
        )
        self.record(path, operation, result)
        return result

    def _node(self, node: object, path: tuple[str | int, ...]) -> RuntimeValue:
        """Исполняет один типизированный узел без eval, getattr или внешних вызовов."""
        if isinstance(node, ParameterReferenceVO):
            value = self.parameter(node.parameter, path)
            assert value is not None
            return value
        if isinstance(node, DecimalLiteralVO):
            return node.value
        if isinstance(node, ScalarLiteralVO):
            return node.value
        if isinstance(node, CollectionLiteralVO):
            return tuple(item.value for item in node.items)
        if isinstance(node, PresenceConditionVO):
            value = self.parameter(
                node.parameter.parameter, (*path, "parameter"), allow_missing=True
            )
            return (
                (value is not None)
                if node.operator.value == "EXISTS"
                else (value is None)
            )
        if isinstance(node, LogicalConditionVO):
            if node.operator.value == "NOT":
                return not self.node(node.operands[0], (*path, "operands", 0))
            for index, operand in enumerate(node.operands):
                value = self.node(operand, (*path, "operands", index))
                if node.operator.value == "ALL" and not value:
                    return False
                if node.operator.value == "ANY" and value:
                    return True
            return node.operator.value == "ALL"
        if isinstance(node, ComparisonConditionVO):
            left = self.node(node.left, (*path, "left"))
            right = self.node(node.right, (*path, "right"))
            op = node.operator.value
            if op == "EQ":
                return left == right
            if op == "NE":
                return left != right
            if op == "IN":
                return left in right
            if op == "NOT_IN":
                return left not in right
            if op == "CONTAINS":
                return right in left
            if op == "GT":
                return left > right
            if op == "GTE":
                return left >= right
            if op == "LT":
                return left < right
            return left <= right
        if isinstance(node, ArithmeticExpressionVO):
            if node.operator.value == "NEGATE":
                return -self.numeric(self.node(node.operand, (*path, "operand")), path)
            left = self.numeric(self.node(node.left, (*path, "left")), (*path, "left"))
            right = self.numeric(
                self.node(node.right, (*path, "right")), (*path, "right")
            )
            op = node.operator.value
            if op == "ADD":
                return left + right
            if op == "SUBTRACT":
                return left - right
            if op == "MULTIPLY":
                return left * right
            if right == 0:
                raise CalculationExecutionError(
                    "DIVISION_BY_ZERO", "Деление на ноль.", path
                )
            return left / right
        if isinstance(node, FunctionExpressionVO):
            values = tuple(
                self.numeric(
                    self.node(item, (*path, "arguments", i)), (*path, "arguments", i)
                )
                for i, item in enumerate(node.arguments)
            )
            if node.function.value == "ABS":
                return abs(values[0])
            return min(values) if node.function.value == "MIN" else max(values)
        raise CalculationExecutionError(
            "INVALID_EXPRESSION_TYPE", "Неизвестный узел.", path
        )


def _numeric_context() -> Context:
    """Создаёт одинаковый числовой бюджет для денежных и логических выражений."""
    context = Context(prec=PRECISION, rounding=ROUND_HALF_UP, Emin=-168, Emax=168)
    context.traps[Underflow] = True
    return context


def calculate_boolean(
    calculation: BooleanCalculationVO, inputs: CalculationInputsVO
) -> BooleanCalculationResult:
    """Выполняет проверенное условие IF тем же вычислителем, что и денежные правила."""
    execution = _Execution(inputs)
    issues: tuple[CalculationIssue, ...] = ()
    value = None
    used_default = False
    try:
        with localcontext(_numeric_context()):
            condition = execution.node(calculation.condition, ("condition",))
        used_default = condition is False
        value = calculation.else_value if used_default else calculation.then_value
        result_path = ("else_value",) if used_default else ("then_value",)
        execution.record(result_path, "ELSE" if used_default else "THEN", value)
    except CalculationExecutionError as exc:
        issues = (CalculationIssue(exc.code, str(exc), exc.path),)
    return BooleanCalculationResult(
        value,
        used_default,
        tuple(execution.steps),
        tuple(execution.used.items()),
        issues,
    )


class MoneyFieldCalculator:
    """Разрешает MONEY-поле одинаково для preview и будущих публикаций/экспорта."""

    @staticmethod
    def calculate(
        field: FieldNodeDefinition,
        inputs: CalculationInputsVO,
        *,
        manual_amount: PriceAmountVO | None = None,
    ) -> PriceCalculationResult:
        """Возвращает точное значение либо адресованную ошибку выбранной ветви."""
        settings = field.type_definition
        if not isinstance(settings, MoneyNodeDataVO):
            raise InvalidFeedValueError("Предпросмотр цены требует MONEY-поле.")
        definition = settings.value_definition
        if (
            definition.source is not None
            and definition.source.path is not CatalogSourcePath.REGULAR_PRICE
        ):
            raise CalculationDefinitionError(
                "INVALID_EXPRESSION_TYPE", "Источник несовместим с денежным полем."
            )
        if manual_amount is None and definition.calculation is not None:
            PriceCalculationSemanticPolicy.ensure_valid(definition.calculation)
        execution = _Execution(inputs)
        selected: UUID | None = None
        used_default = False
        value = None
        issues: tuple[CalculationIssue, ...] = ()
        try:
            with localcontext(_numeric_context()):
                if manual_amount is not None:
                    amount = manual_amount.amount
                elif definition.mode.value == "MANUAL":
                    raise CalculationExecutionError(
                        "MANUAL_VALUE_REQUIRED",
                        "Для ручного поля требуется значение публикации.",
                        ("value",),
                    )
                elif definition.calculation is None:
                    amount = execution.parameter("price.regular", ("value", "source"))
                    execution.record(("value", "source"), "source", amount)
                else:
                    calculation = definition.calculation
                    chosen = calculation.default_expression
                    chosen_path: tuple[str | int, ...] = ("default_expression",)
                    for index, rule in enumerate(calculation.rules):
                        execution.rule_id = rule.id.uuid
                        matched = execution.node(
                            rule.condition, ("rules", index, "condition")
                        )
                        if matched:
                            selected = rule.id.uuid
                            chosen, chosen_path = rule.expression, (
                                "rules",
                                index,
                                "expression",
                            )
                            used_default = False
                            break
                    used_default = selected is None
                    execution.rule_id = selected
                    amount = execution.node(chosen, chosen_path)
                amount = execution.numeric(amount, ("result",))
                for index, transform in enumerate(settings.transforms):
                    if isinstance(transform.parameters, MoneyCeilStepParametersVO):
                        amount = ceil_step(amount, transform.parameters.step)
                        amount = execution.numeric(amount, ("transforms", index))
                        execution.record(
                            ("transforms", index), transform.operation.value, amount
                        )
                constraints = settings.constraints
                if (
                    constraints.min_amount is not None
                    and amount < constraints.min_amount
                ) or (
                    constraints.max_amount is not None
                    and amount > constraints.max_amount
                ):
                    raise CalculationExecutionError(
                        "AMOUNT_CONSTRAINT_VIOLATION",
                        "Сумма не соответствует ограничениям поля.",
                        ("constraints",),
                    )
                value = PriceValueVO(PriceAmountVO(amount), settings.currency)
        except CalculationExecutionError as exc:
            issues = (
                CalculationIssue(exc.code, str(exc), exc.path, execution.rule_id),
            )
        return PriceCalculationResult(
            value,
            selected,
            used_default,
            tuple(execution.steps),
            tuple(execution.used.items()),
            issues,
        )
