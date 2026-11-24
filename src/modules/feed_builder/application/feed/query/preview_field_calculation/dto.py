from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from src.modules.feed_builder.domain.feed.calculation.result import TraceValue


@dataclass(frozen=True, slots=True)
class CalculationPreviewStepDTO:
    """Передаёт фактически выполненный шаг с путём и правилом."""

    path: tuple[str | int, ...]
    operation: str
    value: TraceValue
    rule_id: UUID | None


@dataclass(frozen=True, slots=True)
class CalculationPreviewIssueDTO:
    """Привязывает ошибку к конкретному полю и узлу выражения."""

    code: str
    message: str
    field_id: UUID
    rule_id: UUID | None
    path: tuple[str | int, ...]


@dataclass(frozen=True, slots=True)
class PreviewFieldCalculationResultDTO:
    """Возвращает диагностический результат без выдуманных версий схем/публикаций."""

    feed_id: UUID
    version: int
    field_id: UUID
    definition_hash: str
    catalog_item_id: UUID
    catalog_variant_id: UUID | None
    selected_product_id: UUID
    product_kind: str
    sku: str | None
    source_revision: int
    as_of: datetime
    valid_until: datetime | None
    calculation_engine_version: str
    validation_status: str
    amount: str | None
    currency: str | None
    selected_rule_id: UUID | None
    used_default: bool
    steps: tuple[CalculationPreviewStepDTO, ...]
    parameters: tuple[tuple[str, TraceValue], ...]
    issues: tuple[CalculationPreviewIssueDTO, ...]
    scalar_value: int | bool | None = None
