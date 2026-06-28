from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from src.modules.shared.application.pagination import CursorCodec, InvalidCursorError


@dataclass(frozen=True, slots=True)
class WorkflowApplicationCursor:
    """Workflow application cursor tied to list ordering semantics."""

    created_at: datetime
    id: str

    VERSION = 1
    SORT = "created_at_desc_id_desc"

    def encode(self) -> str:
        return CursorCodec.encode(
            {
                "v": self.VERSION,
                "sort": self.SORT,
                "created_at": self.created_at.isoformat(),
                "id": self.id,
            }
        )

    @classmethod
    def decode(cls, value: str) -> "WorkflowApplicationCursor":
        payload = CursorCodec.decode(value)

        if payload.get("v") != cls.VERSION:
            raise InvalidCursorError("Unsupported workflow cursor version.")
        if payload.get("sort") != cls.SORT:
            raise InvalidCursorError("Invalid workflow cursor sort.")

        try:
            return cls(
                created_at=datetime.fromisoformat(payload["created_at"]),
                id=str(payload["id"]),
            )
        except Exception as exc:
            raise InvalidCursorError("Invalid workflow cursor payload.") from exc

    @classmethod
    def from_item(
        cls,
        item: Any,
    ) -> "WorkflowApplicationCursor":
        return cls(
            created_at=item.created_at,
            id=str(item.id),
        )

    @property
    def uuid(self) -> UUID:
        try:
            return UUID(self.id)
        except ValueError as exc:
            raise InvalidCursorError("Invalid workflow cursor id.") from exc


__all__ = ["WorkflowApplicationCursor"]
