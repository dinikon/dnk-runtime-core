from src.modules.channels.domain.stock_sync.state import DesiredStockVO, StockMode
from typing import Literal
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.stock_sync.aggregate import StockSync
from src.modules.channels.domain.stock_sync.value_object import StockSnapshotVO
from src.modules.channels.infrastructure.persistence.models.stock_sync import (
    StockSyncModel,
)


class StockSnapshotDocument(BaseModel):
    """Версионирование конкретного документа наблюдения."""

    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    resource_type: str
    external_id: str
    mode: str
    quantity: Decimal | None
    availability: str | None
    backorders: str | None


class DesiredStockDocument(BaseModel):
    """Строгий документ желаемого наличия без нативных полей."""

    model_config = ConfigDict(extra="forbid", strict=True)
    version: Literal[1] = 1
    mode: str
    quantity: int | None
    availability: str
    backorders: str

    def to_value(self) -> DesiredStockVO:
        """Передаёт проверку значения доменному VO."""
        return DesiredStockVO(
            StockMode(self.mode), self.quantity, self.availability, self.backorders
        )


def to_domain(row: StockSyncModel) -> StockSync:
    """Восстанавливает через фабрику; инварианты остаются в Domain."""
    observed = (
        StockSnapshotDocument.model_validate(row.observed) if row.observed else None
    )
    return StockSync.restore(
        publication_id=EntityIdVO(row.publication_id),
        connection_id=EntityIdVO(row.connection_id),
        operation_id=EntityIdVO(row.operation_id),
        direction=row.direction,
        status=row.status,
        revision=row.revision,
        config_revision=row.config_revision,
        policy_revision=row.policy_revision,
        binding_group_id=EntityIdVO(row.binding_group_id),
        binding_revision=row.binding_revision,
        observed=(
            StockSnapshotVO(
                observed.resource_type,
                observed.external_id,
                observed.mode,
                observed.quantity,
                observed.availability,
                observed.backorders,
            )
            if observed
            else None
        ),
        observed_at=row.observed_at,
        desired_state=(
            DesiredStockDocument.model_validate(row.desired_state).to_value()
            if row.desired_state
            else None
        ),
        error_code=row.error_code,
        updated_at=row.updated_at,
    )


def to_values(state: StockSync) -> dict[str, object]:
    """Не выполняет запросов и сохраняет Decimal строкой."""
    return {
        "publication_id": state.publication_id.uuid,
        "connection_id": state.connection_id.uuid,
        "operation_id": state.operation_id.uuid,
        "direction": state.direction,
        "status": state.status,
        "revision": state.revision,
        "config_revision": state.config_revision,
        "policy_revision": state.policy_revision,
        "binding_group_id": state.binding_group_id.uuid,
        "binding_revision": state.binding_revision,
        "observed": (
            {"version": 1, **state.observed.to_document()} if state.observed else None
        ),
        "observed_at": state.observed_at,
        "desired_state": (
            state.desired_state.to_document() if state.desired_state else None
        ),
        "error_code": state.error_code,
        "updated_at": state.updated_at,
    }
