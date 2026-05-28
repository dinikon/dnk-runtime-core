from uuid import UUID

from pydantic import BaseModel


class ContactSummaryResponseSchema(BaseModel):
    """HTTP response Contact summary."""

    id: UUID
    first_name: str
    last_name: str | None
    middle_name: str | None
    status: str | None


__all__ = ["ContactSummaryResponseSchema"]
