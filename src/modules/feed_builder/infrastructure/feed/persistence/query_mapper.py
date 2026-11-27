from collections.abc import Mapping
from src.modules.feed_builder.application.feed.query.get_feed.dto import FeedDetailsDTO
from src.modules.feed_builder.application.feed.query.get_feed_schema.dto import (
    FeedSchemaDetailsDTO,
)
from src.modules.feed_builder.application.feed.query.list_feeds.dto import (
    FeedListItemDTO,
)
from src.modules.feed_builder.application.feed.export_settings import settings_to_dto
from src.modules.feed_builder.application.feed.graph.codec import schema_document
from src.modules.feed_builder.infrastructure.feed.persistence.graph_mapper import (
    decode_schema,
)
from src.modules.feed_builder.infrastructure.feed.persistence.settings_mapper import (
    feed_settings_from_document,
)


class FeedQueryMapper:
    """Строит DTO из SQL-проекций без восстановления агрегата Feed."""

    @staticmethod
    def to_schema(row: Mapping[str, object]) -> FeedSchemaDetailsDTO:
        """Возвращает документ и общую версию без восстановления корня."""
        return FeedSchemaDetailsDTO(
            feed_id=row["id"],
            version=row["row_version"],
            status=row["status"],
            definition=schema_document(decode_schema(row["schema_definition"])),
        )

    @staticmethod
    def to_details(row: Mapping[str, object]) -> FeedDetailsDTO:
        """Возвращает карточку и документ графа версии 2."""
        settings, _ = feed_settings_from_document(row["export_settings"])
        return FeedDetailsDTO(
            id=row["id"],
            name=row["name"],
            code=row["code"],
            status=row["status"],
            version=row["row_version"],
            export_settings=settings_to_dto(settings),
            schema=schema_document(decode_schema(row["schema_definition"])),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def to_list_item(row: Mapping[str, object]) -> FeedListItemDTO:
        """Возвращает компактную строку без полного JSON схемы."""
        return FeedListItemDTO(
            id=row["id"],
            name=row["name"],
            code=row["code"],
            status=row["status"],
            format=row["format"],
            fields_count=row["fields_count"],
            version=row["row_version"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
