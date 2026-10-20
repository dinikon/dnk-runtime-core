from collections.abc import Mapping, Sequence
from typing import Any
from src.modules.channels.application.content_update.query.get_content_update.dto import (
    GetContentUpdateResultDTO,
    ContentUpdateItemDTO,
    ContentUpdateTextDTO,
)


class ContentUpdateQueryMapper:
    """Строит read проекцию без восстановления доменного корня."""

    @staticmethod
    def texts(value: Mapping[str, Any] | None) -> tuple[ContentUpdateTextDTO, ...]:
        """Преобразует снимок в безопасные значения UI."""
        return (
            tuple(
                ContentUpdateTextDTO(text["locale"], text["title"], text["body"])
                for text in value["translations"]
            )
            if value
            else ()
        )

    @staticmethod
    def to_details(
        row: Mapping[str, Any],
        items: Sequence[Mapping[str, Any]],
        outbound_enabled: bool,
    ) -> GetContentUpdateResultDTO:
        """Исключает ciphertext, native context и внутренние payload из HTTP проекции."""
        return GetContentUpdateResultDTO(
            row["id"],
            row["channel_id"],
            row["status"],
            row["revision"],
            row["sequence"],
            row["preview_hash"],
            row["created_at"],
            row["expires_at"],
            row["confirmed_at"],
            outbound_enabled,
            tuple(
                ContentUpdateItemDTO(
                    item["publication_id"],
                    item["catalog_item_id"],
                    item["external_id"],
                    ContentUpdateQueryMapper.texts(item["desired"]),
                    ContentUpdateQueryMapper.texts(item["observed"]),
                    item["status"],
                    tuple(item["issues"]),
                    item["attempts"],
                )
                for item in items
            ),
        )
