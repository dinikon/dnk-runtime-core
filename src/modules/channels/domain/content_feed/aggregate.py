from dataclasses import dataclass, field
from datetime import datetime

from src.modules.channels.domain.content_feed.error import ContentFeedError
from src.modules.channels.domain.content_feed.value_object import FeedSourceVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True)
class ContentFeed:
    """Владеет источником, разрешением и отзывным доступом постоянного фида."""

    id: EntityIdVO
    connection_id: EntityIdVO
    scope_key: str
    revision: int
    enabled: bool
    source: FeedSourceVO
    source_url_encrypted: bytes = field(repr=False)
    access_token_hash: bytes | None = field(repr=False)
    access_token_encrypted: bytes | None = field(repr=False)
    created_at: datetime
    updated_at: datetime
    created_by: EntityIdVO
    updated_by: EntityIdVO

    @classmethod
    def create(
        cls,
        *,
        identifier: EntityIdVO,
        connection_id: EntityIdVO,
        source: FeedSourceVO,
        source_url_encrypted: bytes,
        token_hash: bytes,
        token_encrypted: bytes,
        actor: EntityIdVO,
        now: datetime,
    ) -> "ContentFeed":
        """Создаёт выключенный фид полного каталога с первой ревизией."""
        return cls.restore(
            identifier=identifier,
            connection_id=connection_id,
            scope_key="catalog",
            revision=1,
            enabled=False,
            source=source,
            source_url_encrypted=source_url_encrypted,
            access_token_hash=token_hash,
            access_token_encrypted=token_encrypted,
            created_at=now,
            updated_at=now,
            created_by=actor,
            updated_by=actor,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: EntityIdVO,
        connection_id: EntityIdVO,
        scope_key: str,
        revision: int,
        enabled: bool,
        source: FeedSourceVO,
        source_url_encrypted: bytes,
        access_token_hash: bytes | None,
        access_token_encrypted: bytes | None,
        created_at: datetime,
        updated_at: datetime,
        created_by: EntityIdVO,
        updated_by: EntityIdVO,
    ) -> "ContentFeed":
        """Отклоняет повреждённые состояния без автоматического исправления."""
        if (
            not all(
                isinstance(v, EntityIdVO)
                for v in (identifier, connection_id, created_by, updated_by)
            )
            or scope_key != "catalog"
            or type(revision) is not int
            or revision < 1
            or type(enabled) is not bool
            or not isinstance(source, FeedSourceVO)
            or not isinstance(source_url_encrypted, bytes)
            or not source_url_encrypted
            or (access_token_hash is None) != (access_token_encrypted is None)
            or (
                access_token_hash is not None
                and (
                    not isinstance(access_token_hash, bytes)
                    or len(access_token_hash) != 32
                    or not isinstance(access_token_encrypted, bytes)
                    or not access_token_encrypted
                )
            )
            or (enabled and access_token_hash is None)
        ):
            raise ContentFeedError("feed_state_invalid")
        if (
            any(
                not isinstance(v, datetime) or v.tzinfo is None or v.utcoffset() is None
                for v in (created_at, updated_at)
            )
            or updated_at < created_at
        ):
            raise ContentFeedError("feed_audit_invalid")
        return cls(
            identifier,
            connection_id,
            scope_key,
            revision,
            enabled,
            source,
            source_url_encrypted,
            access_token_hash,
            access_token_encrypted,
            created_at,
            updated_at,
            created_by,
            updated_by,
        )

    def require_revision(self, expected_revision: int) -> None:
        """Проверяет версию до любой операции, включая сохранение без изменений."""
        if type(expected_revision) is not int or expected_revision != self.revision:
            raise ContentFeedError("feed_revision_conflict", conflict=True)

    def change_source(
        self,
        *,
        source: FeedSourceVO,
        encrypted_url: bytes,
        expected_revision: int,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Замена источника аннулирует разрешение выдачи."""
        self.require_revision(expected_revision)
        if self.source != source or self.source_url_encrypted != encrypted_url:
            self._change(
                source=source,
                encrypted_url=encrypted_url,
                enabled=False,
                token_hash=self.access_token_hash,
                token_encrypted=self.access_token_encrypted,
                actor=actor,
                now=now,
            )

    def enable(
        self,
        *,
        expected_revision: int,
        blockers: tuple[str, ...],
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Разрешает выдачу только после полной проверки текущего документа."""
        self.require_revision(expected_revision)
        if blockers:
            raise ContentFeedError(blockers[0])
        if self.access_token_hash is None:
            raise ContentFeedError("feed_access_revoked")
        if not self.enabled:
            self._change(
                source=self.source,
                encrypted_url=self.source_url_encrypted,
                enabled=True,
                token_hash=self.access_token_hash,
                token_encrypted=self.access_token_encrypted,
                actor=actor,
                now=now,
            )

    def disable(
        self, *, expected_revision: int, actor: EntityIdVO, now: datetime
    ) -> None:
        """Идемпотентно выключает endpoint с сохранением токена."""
        self.require_revision(expected_revision)
        if self.enabled:
            self._change(
                source=self.source,
                encrypted_url=self.source_url_encrypted,
                enabled=False,
                token_hash=self.access_token_hash,
                token_encrypted=self.access_token_encrypted,
                actor=actor,
                now=now,
            )

    def rotate_access_token(
        self,
        *,
        token_hash: bytes,
        token_encrypted: bytes,
        expected_revision: int,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Немедленно заменяет доступ, не включая ранее выключенный фид."""
        self.require_revision(expected_revision)
        self._change(
            source=self.source,
            encrypted_url=self.source_url_encrypted,
            enabled=self.enabled,
            token_hash=token_hash,
            token_encrypted=token_encrypted,
            actor=actor,
            now=now,
        )

    def revoke_access(
        self, *, expected_revision: int, actor: EntityIdVO, now: datetime
    ) -> None:
        """Отзывает ссылку и выключает фид одним переходом."""
        self.require_revision(expected_revision)
        if self.access_token_hash is not None:
            self._change(
                source=self.source,
                encrypted_url=self.source_url_encrypted,
                enabled=False,
                token_hash=None,
                token_encrypted=None,
                actor=actor,
                now=now,
            )

    def _change(
        self,
        *,
        source: FeedSourceVO,
        encrypted_url: bytes,
        enabled: bool,
        token_hash: bytes | None,
        token_encrypted: bytes | None,
        actor: EntityIdVO,
        now: datetime,
    ) -> None:
        """Проверяет весь кандидат до изменения состояния и единственного шага ревизии."""
        candidate = self.restore(
            identifier=self.id,
            connection_id=self.connection_id,
            scope_key=self.scope_key,
            revision=self.revision + 1,
            enabled=enabled,
            source=source,
            source_url_encrypted=encrypted_url,
            access_token_hash=token_hash,
            access_token_encrypted=token_encrypted,
            created_at=self.created_at,
            updated_at=now,
            created_by=self.created_by,
            updated_by=actor,
        )
        self.source, self.source_url_encrypted = (
            candidate.source,
            candidate.source_url_encrypted,
        )
        self.enabled = candidate.enabled
        self.access_token_hash = candidate.access_token_hash
        self.access_token_encrypted = candidate.access_token_encrypted
        self.revision, self.updated_at, self.updated_by = (
            candidate.revision,
            candidate.updated_at,
            candidate.updated_by,
        )
