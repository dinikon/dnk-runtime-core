from collections.abc import Mapping
from typing import Any

from src.modules.channels.domain.content_feed.aggregate import ContentFeed
from src.modules.channels.domain.content_feed.value_object import FeedSourceVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.infrastructure.content_feed.delivery_document import (
    DELIVERY_SCHEMA,
    decode_delivery,
    encode_delivery,
)


class ContentFeedMapper:
    """Единственная граница SQL-представления и доменного агрегата."""

    @staticmethod
    def to_domain(row: Mapping[str, Any]) -> ContentFeed:
        """Восстанавливает состояние через проверяющую фабрику без исправлений."""
        return ContentFeed.restore(
            identifier=EntityIdVO(row["id"]),
            connection_id=EntityIdVO(row["connection_id"]),
            scope_key=row["scope_key"],
            revision=row["revision"],
            enabled=row["enabled"],
            source=FeedSourceVO(row["source_schema"], row["source_settings"]),
            source_url_encrypted=row["source_url_encrypted"],
            access_token_hash=row["access_token_hash"],
            access_token_encrypted=row["access_token_encrypted"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            created_by=EntityIdVO(row["created_by"]),
            updated_by=EntityIdVO(row["updated_by"]),
            delivery=decode_delivery(row["delivery_schema"], row["delivery_state"]),
            delivery_request_encrypted=row["delivery_request_encrypted"],
        )

    @staticmethod
    def to_values(feed: ContentFeed) -> dict[str, Any]:
        """Возвращает колонки агрегата без SQL или управления транзакцией."""
        return dict(
            id=feed.id.uuid,
            connection_id=feed.connection_id.uuid,
            scope_key=feed.scope_key,
            revision=feed.revision,
            enabled=feed.enabled,
            source_schema=feed.source.schema,
            source_settings=feed.source.settings,
            source_url_encrypted=feed.source_url_encrypted,
            access_token_hash=feed.access_token_hash,
            access_token_encrypted=feed.access_token_encrypted,
            created_at=feed.created_at,
            updated_at=feed.updated_at,
            created_by=feed.created_by.uuid,
            updated_by=feed.updated_by.uuid,
            delivery_schema=DELIVERY_SCHEMA,
            delivery_state=encode_delivery(feed.delivery),
            delivery_request_encrypted=feed.delivery_request_encrypted,
        )
