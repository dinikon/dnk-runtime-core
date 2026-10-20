import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.content_update.entity.item import ContentUpdateItem
from src.modules.channels.domain.content_update.value_object.texts import ContentTextsVO
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsNotFoundError,
)


@dataclass(slots=True)
class ContentUpdateRun:
    """Владеет предпросмотром, подтверждением и доставкой фиксированного набора текстов."""

    id: EntityIdVO
    channel_id: EntityIdVO
    connection_id: EntityIdVO
    actor_id: EntityIdVO
    generation: int
    sdk_version: int
    status: str
    revision: int
    sequence: int
    created_at: datetime
    expires_at: datetime
    confirmed_at: datetime | None
    preview_hash_value: str | None
    items: list[ContentUpdateItem]

    @classmethod
    def create(
        cls,
        identifier: EntityIdVO,
        channel_id: EntityIdVO,
        connection_id: EntityIdVO,
        actor_id: EntityIdVO,
        generation: int,
        sdk_version: int,
        created_at: datetime,
        expires_at: datetime,
        items: list[ContentUpdateItem],
    ) -> Self:
        """Создаёт read-only подготовку; исходящая синхронизация пока не требуется."""
        return cls.restore(
            identifier,
            channel_id,
            connection_id,
            actor_id,
            generation,
            sdk_version,
            "preparing",
            1,
            0,
            created_at,
            expires_at,
            None,
            None,
            items,
        )

    @classmethod
    def restore(
        cls,
        identifier: EntityIdVO,
        channel_id: EntityIdVO,
        connection_id: EntityIdVO,
        actor_id: EntityIdVO,
        generation: int,
        sdk_version: int,
        status: str,
        revision: int,
        sequence: int,
        created_at: datetime,
        expires_at: datetime,
        confirmed_at: datetime | None,
        preview_hash_value: str | None,
        items: list[ContentUpdateItem],
    ) -> Self:
        """Проверяет инварианты корня независимо от представления хранения."""
        if (
            not all(
                isinstance(value, EntityIdVO)
                for value in (identifier, channel_id, connection_id, actor_id)
            )
            or not 1 <= len(items) <= 50
            or len({item.publication_id for item in items}) != len(items)
            or generation < 0
            or sdk_version < 1
            or revision < 1
            or sequence < 0
            or created_at.utcoffset() is None
            or expires_at.utcoffset() is None
            or expires_at <= created_at
            or status
            not in {
                "preparing",
                "ready",
                "blocked",
                "queued",
                "running",
                "succeeded",
                "partial",
                "failed",
                "stale",
            }
        ):
            raise ChannelsConflictError("invalid_content_update_run")
        locales = tuple(text.locale for text in items[0].desired.translations)
        if (
            any(
                tuple(text.locale for text in item.desired.translations) != locales
                for item in items
            )
            or len({item.catalog_item_id for item in items}) != len(items)
            or (
                confirmed_at is not None
                and (
                    confirmed_at.utcoffset() is None
                    or not created_at <= confirmed_at < expires_at
                    or preview_hash_value is None
                )
            )
            or (
                status in {"preparing", "ready", "blocked"} and confirmed_at is not None
            )
            or (
                status in {"queued", "running", "succeeded", "partial", "failed"}
                and confirmed_at is None
            )
        ):
            raise ChannelsConflictError("invalid_content_update_run")
        return cls(
            identifier,
            channel_id,
            connection_id,
            actor_id,
            generation,
            sdk_version,
            status,
            revision,
            sequence,
            created_at,
            expires_at,
            confirmed_at,
            preview_hash_value,
            list(items),
        )

    def ensure_owner(self, actor_id: EntityIdVO) -> None:
        """Не позволяет использовать чужую подготовку и её ключ идемпотентности."""
        if self.actor_id != actor_id:
            raise ChannelsNotFoundError("content_update_not_found")

    def ensure_revision(self, revision: int) -> None:
        """Отклоняет устаревшее действие интерфейса."""
        if self.revision != revision:
            raise ChannelsConflictError("content_update_revision_conflict")

    def preview_hash(self) -> str:
        """Связывает подтверждение с контентом, целями и версией привязки."""
        payload = [
            [
                str(item.publication_id.uuid),
                str(item.binding_id.uuid),
                item.binding_revision,
                item.resource_type,
                item.external_id,
                item.desired.digest(),
                item.observed.digest() if item.observed else None,
                item.status,
                list(item.issues),
            ]
            for item in self.items
        ]
        return hashlib.sha256(
            json.dumps(payload, separators=(",", ":")).encode()
        ).hexdigest()

    def confirm(self, revision: int, preview_hash: str, now: datetime) -> bool:
        """Подтверждает один снимок; повтор успешного подтверждения не ставит второй job."""
        if self.confirmed_at is not None:
            if self.preview_hash_value != preview_hash:
                raise ChannelsConflictError("content_update_preview_stale")
            return False
        self.ensure_revision(revision)
        if (
            self.status != "ready"
            or now >= self.expires_at
            or self.preview_hash_value != preview_hash
        ):
            raise ChannelsConflictError("content_update_preview_stale")
        if not any(item.status == "ready" for item in self.items):
            raise ChannelsConflictError("content_update_no_changes")
        for item in self.items:
            if item.status == "ready":
                item.queue()
        self.confirmed_at, self.status = now, "queued"
        self.revision += 1
        return True

    def current(self, sequence: int) -> ContentUpdateItem | None:
        """Выбирает один ограниченный шаг и защищает от старых заданий."""
        if sequence != self.sequence or self.status not in (
            "preparing",
            "queued",
            "running",
        ):
            return None
        return next(
            (
                item
                for item in self.items
                if item.status
                in ("preview_pending", "pending", "sending", "verifying", "reconciling")
            ),
            None,
        )

    def advance(self) -> bool:
        """Пересчитывает прогресс после одного шага без ложного успеха отправки."""
        self.sequence += 1
        self.revision += 1
        pending = any(
            item.status
            in ("preview_pending", "pending", "sending", "verifying", "reconciling")
            for item in self.items
        )
        if self.confirmed_at is None:
            self.status = (
                "preparing"
                if pending
                else (
                    "ready"
                    if any(item.status in ("ready", "unchanged") for item in self.items)
                    else "blocked"
                )
            )
            if not pending:
                self.preview_hash_value = self.preview_hash()
        elif pending:
            self.status = "running"
        else:
            succeeded = any(
                item.status in ("succeeded", "unchanged") for item in self.items
            )
            failed = any(
                item.status not in ("succeeded", "unchanged") for item in self.items
            )
            self.status = (
                "partial"
                if succeeded and failed
                else "failed" if failed else "succeeded"
            )
        return pending

    def dispatch(self, sequence: int) -> tuple[ContentUpdateItem, str] | None:
        """Фиксирует сетевой intent до commit подготовки шага."""
        item = self.current(sequence)
        if item is None:
            return None
        mode = item.dispatch()
        if self.confirmed_at is not None:
            self.status = "running"
        self.revision += 1
        return item, mode

    def invalidate(self, code: str) -> None:
        """Останавливает неподтверждённые шаги при смене локального источника."""
        for item in self.items:
            if item.status in (
                "preview_pending",
                "ready",
                "pending",
                "sending",
                "verifying",
                "reconciling",
            ):
                item.fail(
                    code, uncertain=item.status in ("sending", "verifying"), stale=True
                )
        self.status = "stale"
        self.revision += 1
        self.sequence += 1

    def apply_step(
        self,
        sequence: int,
        publication_id: EntityIdVO,
        mode: str,
        observed: ContentTextsVO | None,
        issues: tuple[str, ...],
        error_code: str | None,
        uncertain: bool,
    ) -> None:
        """Принимает нормализованный факт только текущего intent позиции."""
        item = self.current(sequence)
        if item is None or item.publication_id != publication_id:
            raise ChannelsConflictError("content_update_step_changed")
        if mode == "preview":
            item.preview(observed, (error_code,) if error_code else issues)
        elif error_code:
            item.fail(
                error_code,
                uncertain=uncertain,
                stale=error_code == "external_content_changed",
            )
        elif mode == "send":
            item.sent()
        elif mode == "verify" and observed is not None:
            item.verified(observed)
        else:
            raise ChannelsConflictError("invalid_content_update_result")

    def recover(self) -> None:
        """Возобновляет потерянный job, сохраняя sending для обязательной сверки."""
        if self.status not in ("preparing", "queued", "running"):
            raise ChannelsConflictError("content_update_retry_unavailable")
        self.sequence += 1
        self.revision += 1

    def retry(self, revision: int) -> None:
        """Разрешает только сверку неуспешной доставки, сохраняя подтверждённый снимок."""
        self.ensure_revision(revision)
        if self.confirmed_at is None or self.status not in ("partial", "failed"):
            raise ChannelsConflictError("content_update_retry_unavailable")
        for item in self.items:
            if item.status in ("failed", "unknown"):
                item.retry()
        if not any(item.status == "reconciling" for item in self.items):
            raise ChannelsConflictError("content_update_retry_unavailable")
        self.status = "queued"
        self.revision += 1
        self.sequence += 1
