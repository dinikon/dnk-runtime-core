from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class IntegrationEvent:
    """Cross-module integration event contract."""

    event_id: UUID
    tenant_id: UUID
    event_type: str
    event_version: int
    aggregate_type: str
    aggregate_id: UUID
    payload: dict[str, Any]
    occurred_at: datetime

    def to_payload(self) -> dict[str, Any]:
        """Serializes the event into a broker/database friendly payload."""
        return {
            "event_id": str(self.event_id),
            "tenant_id": str(self.tenant_id),
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_type": self.aggregate_type,
            "aggregate_id": str(self.aggregate_id),
            "payload": dict(self.payload),
            "occurred_at": self.occurred_at.isoformat(),
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "IntegrationEvent":
        """Builds an integration event from a serialized payload."""
        event_payload = payload.get("payload") or {}
        if not isinstance(event_payload, Mapping):
            raise TypeError("Integration event payload must be a mapping.")
        return cls(
            event_id=UUID(str(payload["event_id"])),
            tenant_id=UUID(str(payload["tenant_id"])),
            event_type=str(payload["event_type"]),
            event_version=int(payload["event_version"]),
            aggregate_type=str(payload["aggregate_type"]),
            aggregate_id=UUID(str(payload["aggregate_id"])),
            payload=dict(event_payload),
            occurred_at=datetime.fromisoformat(str(payload["occurred_at"])),
        )


__all__ = ["IntegrationEvent"]
