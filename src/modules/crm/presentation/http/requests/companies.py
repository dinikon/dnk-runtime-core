from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CreateCompanyRequestSchema(BaseModel):
    last_name: str
    company_name: str
    custom_fields: dict[str, Any | None] = Field(default_factory=dict)


class UpdateCompanyRequestSchema(BaseModel):
    last_name: str
    company_name: str
    custom_fields: dict[str, Any | None] = Field(default_factory=dict)


__all__ = [
    "CreateCompanyRequestSchema",
    "UpdateCompanyRequestSchema",
]
