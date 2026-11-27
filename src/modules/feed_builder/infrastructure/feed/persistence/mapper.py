from datetime import datetime
from typing import TypedDict
from uuid import UUID

from src.modules.feed_builder.application.feed.types import JsonObject
from src.modules.feed_builder.infrastructure.persistence.models.feed import FeedModel

from src.modules.shared.domain.domain_error import DomainError
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.domain.feed.aggregate import Feed
from src.modules.feed_builder.domain.feed.enum.feed_status import FeedStatus
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.value_object.feed_name import FeedNameVO
from src.modules.feed_builder.domain.feed.value_object.feed_code import FeedCodeVO
from src.modules.feed_builder.domain.feed.value_object.feed_version import FeedVersionVO
from src.modules.feed_builder.domain.feed.value_object.feed_public_link_id import (
    FeedPublicLinkIdVO,
)
from src.modules.feed_builder.application.feed.graph.codec import schema_document
from src.modules.feed_builder.infrastructure.feed.persistence.graph_mapper import (
    decode_schema,
)
from src.modules.feed_builder.infrastructure.feed.persistence.settings_mapper import (
    feed_settings_from_document,
    settings_document,
)
from src.modules.feed_builder.infrastructure.feed.persistence.error import (
    InvalidFeedStorageError,
)


class FeedSettingsValues(TypedDict):
    """Содержит изменяемые колонки настроек и их общую версию."""

    name: str
    code: str
    status: str
    row_version: int
    export_settings: JsonObject
    updated_at: datetime
    public_link_id: UUID | None


class FeedUpdateValues(FeedSettingsValues):
    """Дополняет настройки записываемым документом графа."""

    schema_definition: JsonObject


class FeedRow(FeedUpdateValues):
    """Содержит полную типизированную строку хранения Feed."""

    id: UUID
    created_at: datetime


class FeedMapper:
    """Явно преобразует сохранённые значения через Feed.restore без I/O."""

    @staticmethod
    def row_values(row: FeedModel) -> FeedRow:
        """Извлекает имя и тип каждой колонки из ORM-представления."""
        return {
            "id": row.id,
            "name": row.name,
            "code": row.code,
            "status": row.status,
            "row_version": row.row_version,
            "schema_definition": row.schema_definition,
            "export_settings": row.export_settings,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "public_link_id": row.public_link_id,
        }

    @staticmethod
    def to_domain(row: FeedRow, *, schema: FeedSchemaVO | None = None) -> Feed:
        """Восстанавливает настройки и загруженную для сценария схему."""
        try:
            settings, access_mode = feed_settings_from_document(row["export_settings"])
            public_link_id = row["public_link_id"]
            return Feed.restore(
                identifier=FeedIdVO.from_value(row["id"]),
                name=FeedNameVO(row["name"]),
                code=FeedCodeVO(row["code"]),
                status=FeedStatus(row["status"]),
                schema=(
                    decode_schema(row["schema_definition"])
                    if schema is None
                    else schema
                ),
                export_settings=settings,
                version=FeedVersionVO(row["row_version"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                public_link_id=(
                    FeedPublicLinkIdVO.from_value(public_link_id)
                    if public_link_id is not None
                    else None
                ),
                access_mode=access_mode,
            )
        except (DomainError, ValueError, TypeError, KeyError) as exc:
            raise InvalidFeedStorageError(
                "Не удалось восстановить сохранённый Feed."
            ) from exc

    @staticmethod
    def to_insert_values(feed: Feed) -> FeedRow:
        """Возвращает полную строку нового агрегата без выполнения INSERT."""
        return {
            "id": feed.id.uuid,
            "created_at": feed.created_at,
            **FeedMapper.to_update_values(feed),
        }

    @staticmethod
    def to_update_values(feed: Feed) -> FeedUpdateValues:
        """Возвращает настройки и новый документ графа."""
        return {
            **FeedMapper.to_settings_values(feed),
            "schema_definition": schema_document(feed.schema),
        }

    @staticmethod
    def to_settings_values(feed: Feed) -> FeedSettingsValues:
        """Возвращает изменяемые свойства управления фидом."""
        return {
            "name": feed.name.value,
            "code": feed.code.value,
            "status": feed.status.value,
            "row_version": feed.version.value,
            "export_settings": {
                **settings_document(feed.export_settings),
                "access_mode": feed.access_mode.value,
            },
            "updated_at": feed.updated_at,
            "public_link_id": feed.public_link_id.uuid if feed.public_link_id else None,
        }
