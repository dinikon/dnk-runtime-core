from datetime import datetime
from typing import Self
from uuid import UUID
from pydantic import BaseModel, model_serializer
from src.modules.feed_builder.application.feed.query.preview_field_calculation.dto import (
    PreviewFieldCalculationResultDTO,
)
from src.modules.feed_builder.domain.feed.calculation.result import TraceValue


class ResolvedPriceResponse(BaseModel):
    """Передаёт сумму и только явно заданную валютную метку результата."""

    amount: str
    currency: str | None = None

    @model_serializer
    def serialize_value(self) -> dict[str, str]:
        """Опускает код валюты, если пользователь его не указал."""
        return {
            "amount": self.amount,
            **({"currency": self.currency} if self.currency is not None else {}),
        }


class CalculationStepResponse(BaseModel):
    """Передаёт один выполненный шаг вычисления."""

    path: tuple[str | int, ...]
    operation: str
    value: TraceValue
    rule_id: UUID | None


class CalculationParameterValueResponse(BaseModel):
    """Сохраняет отличие отсутствия значения от нуля и пустой строки."""

    id: str
    value: TraceValue


class CalculationIssueResponse(BaseModel):
    """Привязывает ошибку к полю, правилу и узлу."""

    code: str
    message: str
    field_id: UUID
    rule_id: UUID | None
    path: tuple[str | int, ...]


class PreviewFieldCalculationResponse(BaseModel):
    """Передаёт расчётный снимок и объяснение без записи бизнес-состояния."""

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
    resolved_value: ResolvedPriceResponse | bool | int | None
    selected_rule_id: UUID | None
    used_default: bool
    steps: tuple[CalculationStepResponse, ...]
    parameters: tuple[CalculationParameterValueResponse, ...]
    issues: tuple[CalculationIssueResponse, ...]

    @classmethod
    def from_dto(cls, value: PreviewFieldCalculationResultDTO) -> Self:
        """Явно собирает собственную HTTP-схему и сохраняет Decimal как строки."""
        return cls(
            feed_id=value.feed_id,
            version=value.version,
            field_id=value.field_id,
            definition_hash=value.definition_hash,
            catalog_item_id=value.catalog_item_id,
            catalog_variant_id=value.catalog_variant_id,
            selected_product_id=value.selected_product_id,
            product_kind=value.product_kind,
            sku=value.sku,
            source_revision=value.source_revision,
            as_of=value.as_of,
            valid_until=value.valid_until,
            calculation_engine_version=value.calculation_engine_version,
            validation_status=value.validation_status,
            resolved_value=(
                ResolvedPriceResponse(amount=value.amount, currency=value.currency)
                if value.amount is not None
                else value.scalar_value
            ),
            selected_rule_id=value.selected_rule_id,
            used_default=value.used_default,
            steps=tuple(
                CalculationStepResponse(
                    path=step.path,
                    operation=step.operation,
                    value=step.value,
                    rule_id=step.rule_id,
                )
                for step in value.steps
            ),
            parameters=tuple(
                CalculationParameterValueResponse(id=name, value=amount)
                for name, amount in value.parameters
            ),
            issues=tuple(
                CalculationIssueResponse(
                    code=issue.code,
                    message=issue.message,
                    field_id=issue.field_id,
                    rule_id=issue.rule_id,
                    path=issue.path,
                )
                for issue in value.issues
            ),
        )
