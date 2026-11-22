from datetime import datetime
from uuid import UUID
from typing import Self
from pydantic import BaseModel
from src.modules.feed_builder.application.feed.query.list_feeds.dto import (
    ListFeedsResultDTO,
)


class FeedListItemResponse(BaseModel):
    """Передаёт компактную строку списка без схемы."""

    id: UUID
    name: str
    code: str
    status: str
    format: str
    fields_count: int
    version: int
    created_at: datetime
    updated_at: datetime


class ListFeedsResponse(BaseModel):
    """Передаёт страницу и параметры пагинации."""

    items: list[FeedListItemResponse]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_dto(cls, value: ListFeedsResultDTO) -> Self:
        """Явно преобразует строки результата сценария в HTTP-схемы."""
        return cls(
            items=[
                FeedListItemResponse(
                    id=item.id,
                    name=item.name,
                    code=item.code,
                    status=item.status,
                    format=item.format,
                    fields_count=item.fields_count,
                    version=item.version,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
                for item in value.items
            ],
            total=value.total,
            limit=value.limit,
            offset=value.offset,
        )
