from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RequestFeedRefreshCommand:
    """Запрашивает пересборку сохранённого CSV."""

    tenant_id: UUID
    user_id: UUID
    feed_id: UUID
    expected_version: int
