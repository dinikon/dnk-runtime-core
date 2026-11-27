from collections.abc import Mapping

from src.modules.feed_builder.domain.access_key.aggregate import FeedAccessKey
from src.modules.feed_builder.domain.access_key.enum.access_key_status import (
    AccessKeyStatus,
)
from src.modules.feed_builder.domain.access_key.value_object.access_key_name import (
    AccessKeyNameVO,
)
from src.modules.feed_builder.domain.access_key.value_object.access_token_hash import (
    AccessTokenHashVO,
)
from src.modules.feed_builder.domain.access_key.value_object.feed_access_key_id import (
    FeedAccessKeyIdVO,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO


class FeedAccessKeyMapper:
    """Преобразует модель хранения и агрегат ключа."""

    @staticmethod
    def to_domain(row: Mapping[str, object]) -> FeedAccessKey:
        """Восстанавливает агрегат, выводя состояние из даты отзыва."""
        return FeedAccessKey.restore(
            identifier=FeedAccessKeyIdVO.from_value(row["id"]),
            feed_id=FeedIdVO.from_value(row["feed_id"]),
            token_hash=AccessTokenHashVO(row["token_hash"]),
            name=AccessKeyNameVO(row["name"]),
            status=(
                AccessKeyStatus.REVOKED
                if row["revoked_at"] is not None
                else AccessKeyStatus.ACTIVE
            ),
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            revoked_at=row["revoked_at"],
        )

    @staticmethod
    def to_insert_values(key: FeedAccessKey) -> dict[str, object]:
        """Готовит для записи только digest и метаданные."""
        return {
            "id": key.id.uuid,
            "feed_id": key.feed_id.uuid,
            "token_hash": key.token_hash.value,
            "name": key.name.value,
            "created_at": key.created_at,
            "expires_at": key.expires_at,
            "revoked_at": key.revoked_at,
        }
