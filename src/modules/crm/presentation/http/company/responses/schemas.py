from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field
from src.modules.crm.presentation.http.contact_points import ContactPointResponse


class CompanyResponse(BaseModel):
    """HTTP-представление CRM-компании."""

    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID
    phones: list[ContactPointResponse] = Field(default_factory=list)
    emails: list[ContactPointResponse] = Field(default_factory=list)


class CompanyListResponse(BaseModel):
    """Offset-страница CRM-компаний."""

    items: list[CompanyResponse]
    total: int
    limit: int
    offset: int


__all__ = ["CompanyListResponse", "CompanyResponse"]
