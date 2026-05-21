from __future__ import annotations

from pydantic import BaseModel

from src.modules.crm.presentation.http.contact.responses.contact_response import (
    ContactResponseSchema,
)


class ContactSearchPaginationResponseSchema(BaseModel):
    """Pagination envelope for contact search responses."""

    limit: int
    offset: int
    total: int


class ContactSearchResponseSchema(BaseModel):
    """HTTP response schema for contact search."""

    data: list[ContactResponseSchema]
    pagination: ContactSearchPaginationResponseSchema


__all__ = [
    "ContactSearchPaginationResponseSchema",
    "ContactSearchResponseSchema",
]
