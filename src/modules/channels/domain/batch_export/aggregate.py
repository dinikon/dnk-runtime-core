from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Self
from uuid import UUID
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsValidationError,
)

ACTIVE = (
    "preparing",
    "building",
    "checking",
    "ready",
    "submitting",
    "processing",
    "verifying",
    "unknown",
)
TERMINAL = ("succeeded", "partial", "failed", "empty", "prepared")


@dataclass(slots=True)
class BatchExportRun:
    """Владеет снимком пакета и правом единственной отправки подключения."""

    id: UUID
    channel_id: UUID
    connection_id: UUID
    actor_id: UUID | None
    generation: int
    trigger: str
    status: str
    sequence: int
    created_at: datetime
    updated_at: datetime
    remote_id: str | None
    artifact_hash: str | None
    artifact_size: int | None
    expires_at: datetime
    error_code: str | None
    attempts: int
    identity_cursor: str | None = None
    delivery_mode: str = "provider"

    @classmethod
    def create(
        cls,
        identifier: UUID,
        channel_id: UUID,
        connection_id: UUID,
        actor_id: UUID | None,
        generation: int,
        trigger: str,
        now: datetime,
        *,
        delivery_mode: str = "provider",
    ) -> Self:
        """Создаёт пакет без сетевых действий и автоматического разрешения записи."""
        return cls.restore(
            identifier,
            channel_id,
            connection_id,
            actor_id,
            generation,
            trigger,
            "preparing",
            0,
            now,
            now,
            None,
            None,
            None,
            now + timedelta(days=7),
            None,
            0,
            delivery_mode=delivery_mode,
        )

    @classmethod
    def restore(
        cls,
        identifier: UUID,
        channel_id: UUID,
        connection_id: UUID,
        actor_id: UUID | None,
        generation: int,
        trigger: str,
        status: str,
        sequence: int,
        created_at: datetime,
        updated_at: datetime,
        remote_id: str | None,
        artifact_hash: str | None,
        artifact_size: int | None,
        expires_at: datetime,
        error_code: str | None,
        attempts: int,
        identity_cursor: str | None = None,
        delivery_mode: str = "provider",
    ) -> Self:
        """Отклоняет некорректное восстановление состояния доставки."""
        if (
            any(
                not isinstance(value, UUID)
                for value in (identifier, channel_id, connection_id)
            )
            or (actor_id is not None and not isinstance(actor_id, UUID))
            or status not in (*ACTIVE, *TERMINAL)
            or trigger not in ("manual", "daily")
            or delivery_mode not in ("provider", "file")
            or (trigger == "daily" and delivery_mode != "provider")
            or (status == "prepared" and delivery_mode != "file")
            or generation < 0
            or sequence < 0
            or attempts < 0
            or any(v.utcoffset() is None for v in (created_at, updated_at, expires_at))
            or expires_at <= created_at
            or (remote_id is not None and not remote_id)
            or (artifact_hash is not None and len(artifact_hash) != 64)
            or (artifact_size is not None and artifact_size < 1)
        ):
            raise ChannelsValidationError("invalid_batch_export_state")
        return cls(
            identifier,
            channel_id,
            connection_id,
            actor_id,
            generation,
            trigger,
            status,
            sequence,
            created_at,
            updated_at,
            remote_id,
            artifact_hash,
            artifact_size,
            expires_at,
            error_code,
            attempts,
            identity_cursor,
            delivery_mode,
        )

    def advance(self, expected: str, target: str, now: datetime) -> None:
        """Применяет только допустимый переход текущего шага."""
        transitions = {
            "preparing": ("checking", "empty"),
            "building": ("ready",),
            "checking": ("building", "empty"),
            "ready": ("submitting", "prepared"),
            "submitting": ("processing", "unknown"),
            "processing": ("verifying",),
            "verifying": ("succeeded", "partial", "failed", "unknown"),
            "unknown": ("verifying",),
        }
        if self.status != expected or target not in transitions.get(expected, ()):
            raise ChannelsConflictError("batch_export_step_changed")
        self.status = target
        self.touch(now)

    def touch(self, now: datetime) -> None:
        """Выдаёт следующий номер durable шага и обновляет аудит."""
        self.sequence += 1
        self.updated_at = now

    def artifact_ready(self, digest: str, size: int, now: datetime) -> None:
        """Фиксирует неизменяемый файл до допуска к отправке."""
        if self.status != "building" or len(digest) != 64 or size < 1:
            raise ChannelsConflictError("batch_export_artifact_changed")
        self.artifact_hash, self.artifact_size = digest, size
        self.advance("building", "ready", now)

    def claim_submission(self, now: datetime) -> None:
        """До HTTP фиксирует неопределённость: повторная доставка не повторяет POST."""
        if self.artifact_hash is None or self.delivery_mode != "provider":
            raise ChannelsConflictError("batch_export_artifact_missing")
        self.advance("ready", "submitting", now)

    def complete_file(self, now: datetime) -> None:
        """Завершает подготовку для ручного использования без отправки и удержания слота."""
        if self.delivery_mode != "file" or self.artifact_hash is None:
            raise ChannelsConflictError("batch_export_artifact_missing")
        self.advance("ready", "prepared", now)

    def accepted(self, remote_id: str, now: datetime) -> None:
        """Сохраняет ID внешнего процесса без объявления успеха."""
        if not remote_id or len(remote_id) > 200:
            raise ChannelsValidationError("invalid_batch_export_remote_id")
        self.remote_id = remote_id
        self.advance("submitting", "processing", now)
        self.attempts = 0

    def fail(self, reason: str, now: datetime, *, uncertain: bool = False) -> None:
        """Сохраняет безопасную причину; неоднозначный POST удерживает слот."""
        if self.status in TERMINAL:
            raise ChannelsConflictError("batch_export_already_finished")
        self.status = "unknown" if uncertain else "failed"
        self.error_code = reason
        self.touch(now)

    def wait(self, now: datetime) -> None:
        """Ограничивает наблюдение; не разрешает повторную отправку по таймауту."""
        self.attempts += 1
        self.touch(now)
        if self.attempts >= 60:
            self.status, self.error_code = (
                "unknown",
                "batch_export_confirmation_timeout",
            )

    def scanned(self, cursor: str | None, now: datetime) -> None:
        """Продолжает полный обход идентификаторов перед единственной отправкой."""
        if self.status != "checking" or (
            cursor is not None and cursor == self.identity_cursor
        ):
            raise ChannelsConflictError("batch_export_cursor_changed")
        self.identity_cursor = cursor
        self.touch(now)

    def reconcile(self, now: datetime) -> None:
        """Повторяет наблюдение неопределённой отправки без второго POST."""
        if self.status != "unknown":
            raise ChannelsConflictError("batch_export_not_uncertain")
        self.status = "processing" if self.remote_id is not None else "verifying"
        self.attempts = 0
        self.error_code = None
        self.touch(now)

    def note_provider_failure(self) -> None:
        """Сохраняет отказ внешнего процесса, оставляя проверку каждой карточки."""
        self.error_code = "provider_import_failed"

    def finish_item(self, now: datetime) -> None:
        """Сбрасывает бюджет наблюдения для следующей независимой цели."""
        self.attempts = 0
        self.touch(now)
