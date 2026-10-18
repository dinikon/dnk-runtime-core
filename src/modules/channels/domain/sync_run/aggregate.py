from dataclasses import dataclass
from datetime import datetime
from typing import Self
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsValidationError,
)
from src.modules.channels.domain.external_publication.value_object.core import JsonValue


@dataclass(slots=True)
class SyncRun:
    """Управляет ограниченными шагами первичной загрузки одного Connection."""

    id: EntityIdVO
    channel_id: EntityIdVO
    connection_id: EntityIdVO
    generation: int
    status: str
    checkpoint: dict[str, JsonValue]
    sequence: int
    processed: int
    invalid: int
    failures: int
    reason_code: str | None
    limitations: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
    actor_id: EntityIdVO
    request_keys: tuple[str, ...]
    job_id: EntityIdVO | None
    read_complete: bool = False

    @classmethod
    def create(
        cls,
        identifier: EntityIdVO,
        channel_id: EntityIdVO,
        connection_id: EntityIdVO,
        generation: int,
        actor_id: EntityIdVO,
        request_key: EntityIdVO,
        limitations: tuple[str, ...],
        now: datetime,
    ) -> Self:
        """Создаёт единственный queued run с пустым checkpoint."""
        return cls.restore(
            identifier,
            channel_id,
            connection_id,
            generation,
            "queued",
            {},
            0,
            0,
            0,
            0,
            None,
            limitations,
            now,
            now,
            actor_id,
            (str(request_key),),
            None,
        )

    @classmethod
    def restore(
        cls,
        identifier: EntityIdVO,
        channel_id: EntityIdVO,
        connection_id: EntityIdVO,
        generation: int,
        status: str,
        checkpoint: dict[str, JsonValue],
        sequence: int,
        processed: int,
        invalid: int,
        failures: int,
        reason_code: str | None,
        limitations: tuple[str, ...],
        created_at: datetime,
        updated_at: datetime,
        actor_id: EntityIdVO,
        request_keys: tuple[str, ...],
        job_id: EntityIdVO | None,
        read_complete: bool = False,
    ) -> Self:
        """Восстанавливает прогресс без повторного запуска процесса."""
        if not all(
            isinstance(value, EntityIdVO)
            for value in (identifier, channel_id, connection_id, actor_id)
        ) or (job_id is not None and not isinstance(job_id, EntityIdVO)):
            raise ChannelsValidationError("invalid_run_identifier")
        if (
            status
            not in ("queued", "running", "succeeded", "partial", "failed", "cancelled")
            or min(sequence, processed, invalid, failures) < 0
            or (status == "succeeded" and (not read_complete))
            or (created_at.utcoffset() is None)
            or (updated_at.utcoffset() is None)
        ):
            raise ChannelsValidationError("invalid_run_state")
        return cls(
            identifier,
            channel_id,
            connection_id,
            generation,
            status,
            checkpoint,
            sequence,
            processed,
            invalid,
            failures,
            reason_code,
            limitations,
            created_at,
            updated_at,
            actor_id,
            request_keys,
            job_id,
            read_complete,
        )

    def register_request(self, request_key: EntityIdVO) -> None:
        """Закрепляет coalesced запрос за run, сохраняя идемпотентность после завершения."""
        if str(request_key) not in self.request_keys:
            self.request_keys = (*self.request_keys, str(request_key))

    def schedule(self, job_id: EntityIdVO) -> None:
        """Закрепляет job текущего шага для повторов и диагностики."""
        self.ensure_step(self.sequence)
        self.job_id = job_id

    def ensure_step(self, sequence: int) -> None:
        """Защищает счётчики и checkpoint от повторного применения страницы."""
        if self.status not in ("queued", "running") or sequence != self.sequence:
            raise ChannelsConflictError("run_step_changed")

    def advance(
        self,
        checkpoint: dict[str, JsonValue],
        processed: int,
        invalid: int,
        complete: bool,
        now: datetime,
    ) -> None:
        """Атомарно принимает одну порцию и готовит следующий номер шага."""
        self.ensure_step(self.sequence)
        if not complete and checkpoint == self.checkpoint:
            raise ChannelsConflictError("cursor_did_not_advance")
        self.status = "running"
        self.checkpoint = checkpoint
        self.read_complete = complete
        self.sequence += 1
        self.processed += processed
        self.invalid += invalid
        self.failures, self.reason_code = (0, None)
        self.updated_at = now

    def finish(self, now: datetime) -> None:
        """Фиксирует полный обход и явно отмечает ограничения охвата."""
        if not self.read_complete or self.status != "running":
            raise ChannelsConflictError("initialization_not_complete")
        self.status = "partial" if self.invalid or self.limitations else "succeeded"
        self.reason_code = (
            "scope_limited"
            if self.limitations
            else "invalid_rows" if self.invalid else None
        )
        self.updated_at = now

    def fail(self, reason: str, now: datetime, retryable: bool = False) -> bool:
        """Ограничивает повторы сетевого шага и сохраняет частичный результат."""
        self.ensure_step(self.sequence)
        self.failures += 1
        self.reason_code, self.updated_at = (reason, now)
        if retryable and self.failures < 4:
            self.sequence += 1
            return True
        self.status = "partial" if self.processed else "failed"
        return False

    def cancel(self, now: datetime) -> None:
        """Останавливает run, сохраняя уже прочитанные публикации."""
        if self.status in ("queued", "running"):
            self.status, self.reason_code, self.updated_at = (
                "cancelled",
                "connection_changed_or_paused",
                now,
            )

    def retry(
        self,
        request_key: EntityIdVO,
        generation: int,
        limitations: tuple[str, ...],
        now: datetime,
    ) -> None:
        """Возобновляет неполный обход той же generation, сохраняя checkpoint."""
        if (
            self.status not in ("failed", "partial", "cancelled")
            or self.read_complete
            or self.generation != generation
        ):
            raise ChannelsConflictError("new_initialization_run_required")
        self.generation, self.status = (generation, "queued")
        self.read_complete = False
        self.limitations = limitations
        self.sequence += 1
        self.failures, self.reason_code = (0, None)
        self.request_keys = (*self.request_keys, str(request_key))
        self.updated_at = now
