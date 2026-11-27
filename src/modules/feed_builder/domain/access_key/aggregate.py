from dataclasses import dataclass, replace
from datetime import datetime
from typing import Self
from src.modules.feed_builder.domain.access_key.enum.access_key_status import (
    AccessKeyStatus,
)
from src.modules.feed_builder.domain.access_key.error import InvalidAccessKeyValueError
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
from src.modules.feed_builder.domain.validation import require_datetime


@dataclass(frozen=True, slots=True)
class FeedAccessKey:
    """Самостоятельный агрегат ключа чтения публичного файла одного фида."""

    id: FeedAccessKeyIdVO
    feed_id: FeedIdVO
    token_hash: AccessTokenHashVO
    status: AccessKeyStatus
    created_at: datetime
    revoked_at: datetime | None
    name: AccessKeyNameVO
    expires_at: datetime | None

    @classmethod
    def create(
        cls,
        *,
        identifier: FeedAccessKeyIdVO,
        feed_id: FeedIdVO,
        token_hash: AccessTokenHashVO,
        now: datetime,
        name: AccessKeyNameVO,
        expires_at: datetime | None = None,
    ) -> Self:
        """Создаёт активный ключ из готового digest, не генерируя секрет."""
        return cls.restore(
            identifier=identifier,
            feed_id=feed_id,
            token_hash=token_hash,
            status=AccessKeyStatus.ACTIVE,
            created_at=now,
            revoked_at=None,
            name=name,
            expires_at=expires_at,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: FeedAccessKeyIdVO,
        feed_id: FeedIdVO,
        token_hash: AccessTokenHashVO,
        status: AccessKeyStatus,
        created_at: datetime,
        revoked_at: datetime | None,
        name: AccessKeyNameVO,
        expires_at: datetime | None = None,
    ) -> Self:
        """Проверяет согласованность статуса и даты отзыва сохранённого ключа."""
        if (
            not isinstance(identifier, FeedAccessKeyIdVO)
            or not isinstance(feed_id, FeedIdVO)
            or not isinstance(token_hash, AccessTokenHashVO)
            or not isinstance(status, AccessKeyStatus)
            or not isinstance(name, AccessKeyNameVO)
        ):
            raise InvalidAccessKeyValueError("Нужны типизированные свойства ключа.")
        require_datetime(created_at, error=InvalidAccessKeyValueError)
        if expires_at is not None:
            require_datetime(expires_at, error=InvalidAccessKeyValueError)
            if expires_at <= created_at:
                raise InvalidAccessKeyValueError(
                    "Срок действия должен быть позже выпуска."
                )
        if revoked_at is not None:
            require_datetime(revoked_at, error=InvalidAccessKeyValueError)
            if revoked_at < created_at:
                raise InvalidAccessKeyValueError("Отзыв предшествует созданию ключа.")
        if (status is AccessKeyStatus.REVOKED) != (revoked_at is not None):
            raise InvalidAccessKeyValueError(
                "Статус ключа не соответствует дате отзыва."
            )
        return cls(
            id=identifier,
            feed_id=feed_id,
            token_hash=token_hash,
            status=status,
            created_at=created_at,
            revoked_at=revoked_at,
            name=name,
            expires_at=expires_at,
        )

    def revoke(self, *, now: datetime) -> Self:
        """Отзывает конкретный ключ, сохраняя дату первого отзыва."""
        if self.status is AccessKeyStatus.REVOKED:
            return self
        require_datetime(now, error=InvalidAccessKeyValueError)
        if now < self.created_at:
            raise InvalidAccessKeyValueError("Отзыв предшествует созданию ключа.")
        return replace(self, status=AccessKeyStatus.REVOKED, revoked_at=now)
