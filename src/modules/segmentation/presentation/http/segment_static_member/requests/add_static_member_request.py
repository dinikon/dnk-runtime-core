from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class AddStaticMemberRequestSchema(BaseModel):
    """Request body for adding Contact to a static segment."""

    contact_id: UUID
    source_type: Literal["manual", "import", "api"] = "manual"
    metadata: dict[str, Any] | None = None


__all__ = ["AddStaticMemberRequestSchema"]
