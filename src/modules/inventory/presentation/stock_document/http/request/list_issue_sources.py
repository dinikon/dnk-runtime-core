from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ListIssueSourcesRequest(BaseModel):
    """Задаёт серверный поиск и пагинацию источников одной строки."""

    model_config = ConfigDict(extra="forbid")
    document_line_id: UUID
    search: str | None = Field(default=None, max_length=200)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)
    position_id: UUID | None = None
