from collections.abc import Mapping

from src.modules.shared.domain.domain_error import DomainError
from src.modules.feed_builder.domain.feed.aggregate import Feed
from src.modules.feed_builder.domain.feed.enum.feed_status import FeedStatus
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.value_object.feed_name import FeedNameVO
from src.modules.feed_builder.domain.feed.value_object.feed_code import FeedCodeVO
from src.modules.feed_builder.domain.feed.value_object.feed_version import FeedVersionVO
from src.modules.feed_builder.domain.feed.value_object.feed_public_link_id import (
    FeedPublicLinkIdVO,
)
from src.modules.feed_builder.application.feed.schema_document import schema_document
from src.modules.feed_builder.infrastructure.feed.persistence.definition_mapper import (
    decode_schema,
)
from src.modules.feed_builder.infrastructure.feed.persistence.settings_mapper import (
    settings_document,
    settings_from_document,
)
from src.modules.feed_builder.infrastructure.feed.persistence.error import (
    InvalidFeedStorageError,
)


class FeedMapper:
    """Явно преобразует сохранённые значения через Feed.restore без I/O."""

    @staticmethod
    def to_domain(row: Mapping[str, object]) -> Feed:
        """Восстанавливает все свойства, не подставляя потерянную схему или настройки."""
        try:
            return Feed.restore(
                identifier=FeedIdVO.from_value(row["id"]),
                name=FeedNameVO(row["name"]),
                code=FeedCodeVO(row["code"]),
                status=FeedStatus(row["status"]),
                schema=decode_schema(row["schema_definition"]),
                export_settings=settings_from_document(row["export_settings"]),
                version=FeedVersionVO(row["row_version"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                public_link_id=(
                    FeedPublicLinkIdVO.from_value(row["public_link_id"])
                    if row["public_link_id"] is not None
                    else None
                ),
            )
        except (DomainError, ValueError, TypeError, KeyError) as exc:
            raise InvalidFeedStorageError(
                "Не удалось восстановить сохранённый Feed."
            ) from exc

    @staticmethod
    def to_insert_values(feed: Feed) -> dict[str, object]:
        """Возвращает полную строку нового агрегата без выполнения INSERT."""
        return {
            "id": feed.id.uuid,
            "name": feed.name.value,
            "code": feed.code.value,
            "status": feed.status.value,
            "row_version": feed.version.value,
            "schema_definition": schema_document(feed.schema),
            "export_settings": settings_document(feed.export_settings),
            "created_at": feed.created_at,
            "updated_at": feed.updated_at,
            "public_link_id": feed.public_link_id.uuid if feed.public_link_id else None,
        }

    @staticmethod
    def to_update_values(feed: Feed) -> dict[str, object]:
        """Возвращает изменяемое состояние, не переписывая ID и дату создания."""
        values = FeedMapper.to_insert_values(feed)
        del values["id"]
        del values["created_at"]
        return values
