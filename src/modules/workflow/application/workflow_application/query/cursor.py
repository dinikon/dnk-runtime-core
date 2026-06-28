from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class WorkflowApplicationCursor:
    """Opaque cursor payload for workflow application pagination."""

    created_at: datetime
    id: UUID

    @classmethod
    def decode(cls, raw_cursor: str) -> "WorkflowApplicationCursor":
        """Decodes public cursor string into application cursor data."""
        try:
            padded = raw_cursor + "=" * (-len(raw_cursor) % 4)
            decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
            payload = json.loads(decoded.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Workflow cursor payload must be an object.")
            created_at = payload.get("created_at")
            workflow_id = payload.get("id")
            if not isinstance(created_at, str) or not isinstance(workflow_id, str):
                raise ValueError("Workflow cursor payload is incomplete.")
            return cls(
                created_at=datetime.fromisoformat(created_at),
                id=UUID(workflow_id),
            )
        except (binascii.Error, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid workflow cursor.") from exc

    def encode(self) -> str:
        """Encodes application cursor data into public cursor string."""
        payload = {
            "created_at": self.created_at.isoformat(),
            "id": str(self.id),
        }
        encoded = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
        return encoded.decode("ascii").rstrip("=")


__all__ = ["WorkflowApplicationCursor"]
