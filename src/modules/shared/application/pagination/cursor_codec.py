from __future__ import annotations

import base64
import json
from typing import Any

from src.modules.shared.application.pagination.errors import InvalidCursorError


class CursorCodec:
    """Codec for opaque base64url JSON cursor payloads."""

    @staticmethod
    def encode(payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

    @staticmethod
    def decode(value: str) -> dict[str, Any]:
        try:
            padded = value + "=" * (-len(value) % 4)
            raw = base64.urlsafe_b64decode(padded.encode("utf-8"))
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise InvalidCursorError("Invalid cursor.") from exc

        if not isinstance(payload, dict):
            raise InvalidCursorError("Cursor payload must be an object.")

        return payload


__all__ = ["CursorCodec"]
