from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class HandleProviderWebhookCommand:
    tenant_id: UUID
    provider_code: str
    raw_payload: dict[str, Any]


__all__ = ["HandleProviderWebhookCommand"]
