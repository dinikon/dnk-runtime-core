from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class WebhookResultDTO:
    accepted: bool
    matched: bool
    outbound_message_id: UUID | None
    internal_status: str | None


__all__ = ["WebhookResultDTO"]
