from dataclasses import dataclass, field

from src.modules.channels.application.stock_sync.service import StockPlanItem
from src.modules.channels.application.stock_sync.ports import StockPublication
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)


@dataclass(frozen=True, slots=True)
class StockWorkSnapshot:
    """Неизменяемый контекст одного сетевого шага без живой сессии."""

    platform_kind: str
    config: ConnectionConfigVO
    encrypted_credentials: bytes = field(repr=False)
    direction: str
    state_revision: int
    plan: StockPlanItem
    family: tuple[StockPublication, ...]
