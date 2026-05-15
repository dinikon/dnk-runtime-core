from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ProcessQueuedMessagesCommand:
    """Команда обработки очереди outbound messages."""

    tenant_id: EntityIdVO
    limit: int = 100


__all__ = ["ProcessQueuedMessagesCommand"]
