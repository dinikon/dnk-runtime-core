from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from src.modules.channels.application.content_update.query.get_content_update.dto import (
    GetContentUpdateResultDTO,
)


class ContentUpdateTextResponse(BaseModel):
    """Передаёт разрешённые тексты одной локали."""

    locale: str
    title: str | None
    body: str | None


class ContentUpdateItemResponse(BaseModel):
    """Показывает сравнение и результат одной публикации."""

    publication_id: UUID
    catalog_item_id: UUID
    external_id: str
    desired: list[ContentUpdateTextResponse]
    observed: list[ContentUpdateTextResponse]
    status: str
    issues: list[str]
    attempts: int


class GetContentUpdateResponse(BaseModel):
    """Описывает страницу предпросмотра и фоновой доставки."""

    id: UUID
    channel_id: UUID
    status: str
    revision: int
    sequence: int
    preview_hash: str | None
    created_at: datetime
    expires_at: datetime
    confirmed_at: datetime | None
    outbound_enabled: bool
    interrupted: bool
    items: list[ContentUpdateItemResponse]

    @classmethod
    def from_dto(cls, result: GetContentUpdateResultDTO) -> "GetContentUpdateResponse":
        """Создаёт явную HTTP схему без native данных и секретов."""
        return cls(
            id=result.id,
            channel_id=result.channel_id,
            status=result.status,
            revision=result.revision,
            sequence=result.sequence,
            preview_hash=result.preview_hash,
            created_at=result.created_at,
            expires_at=result.expires_at,
            confirmed_at=result.confirmed_at,
            outbound_enabled=result.outbound_enabled,
            interrupted=result.interrupted,
            items=[
                ContentUpdateItemResponse(
                    publication_id=item.publication_id,
                    catalog_item_id=item.catalog_item_id,
                    external_id=item.external_id,
                    status=item.status,
                    issues=list(item.issues),
                    attempts=item.attempts,
                    desired=[
                        ContentUpdateTextResponse(
                            locale=text.locale, title=text.title, body=text.body
                        )
                        for text in item.desired
                    ],
                    observed=[
                        ContentUpdateTextResponse(
                            locale=text.locale, title=text.title, body=text.body
                        )
                        for text in item.observed
                    ],
                )
                for item in result.items
            ],
        )
