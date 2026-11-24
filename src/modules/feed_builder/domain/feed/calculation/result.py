from dataclasses import dataclass
from uuid import UUID
from src.modules.feed_builder.domain.feed.value_object.price_value import PriceValueVO

type TraceValue = str | bool | tuple[str | bool, ...] | None


@dataclass(frozen=True, slots=True)
class CalculationStep:
    """Описывает один реально исполненный узел, условие или преобразование."""

    path: tuple[str | int, ...]
    operation: str
    value: TraceValue
    rule_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class CalculationIssue:
    """Сообщает об ошибке выбранной ветви или ограничения конкретного поля."""

    code: str
    message: str
    path: tuple[str | int, ...]
    rule_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class BooleanCalculationResult:
    """Передаёт итог логического расчёта и исполненные условия."""

    value: bool | None
    used_default: bool
    steps: tuple[CalculationStep, ...]
    parameters: tuple[tuple[str, TraceValue], ...]
    issues: tuple[CalculationIssue, ...]


@dataclass(frozen=True, slots=True)
class PriceCalculationResult:
    """Передаёт итог и объяснение без состояния публикации или сохранения БД."""

    value: PriceValueVO | None
    selected_rule_id: UUID | None
    used_default: bool
    steps: tuple[CalculationStep, ...]
    parameters: tuple[tuple[str, TraceValue], ...]
    issues: tuple[CalculationIssue, ...]
