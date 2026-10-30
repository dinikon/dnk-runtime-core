from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetBindingStockQuery:
    """Параметры локального чтения без обращения к площадке."""

    channel_id: UUID
    group_id: UUID
