from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RotateFeedPublicLinkCommand:
    """Заменяет текущую ссылку в указанной версии Feed."""

    feed_id: UUID
    expected_version: int
