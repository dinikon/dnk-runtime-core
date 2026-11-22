from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID
from src.modules.feed_builder.domain.feed.value_object.calculation_inputs import (
    CalculationInputsVO,
)


@dataclass(frozen=True, slots=True)
class CalculationProductSnapshot:
    """Передаёт собственный снимок FeedBuilder, не раскрывая Domain Catalog."""

    item_id: UUID
    variant_id: UUID | None
    selected_id: UUID
    kind: str
    revision: int
    valid_until: datetime | None
    inputs: CalculationInputsVO


class CalculationProductNotFoundError(Exception):
    """Сообщает об отсутствии доступной выбранной позиции."""


class CalculationDependencyUnavailableError(Exception):
    """Отличает технический сбой источника от отсутствующей цены."""


class CalculationProductReaderProtocol(Protocol):
    """Изолирует чтение выбранной продаваемой позиции от вычислителя Feed."""

    async def read(
        self, item_id: UUID, variant_id: UUID | None, as_of: datetime
    ) -> CalculationProductSnapshot:
        """Получает согласованные цены и revision без автоматического выбора варианта."""
        ...
