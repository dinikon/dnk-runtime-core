"""Жизненный цикл одного обхода внешних публикаций."""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import json

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.types import JsonObject
from src.modules.channels.domain.sync_run.error import InvalidSyncRunError


class SyncRunStatus(StrEnum):
    """Состояния одного запуска, не состояния отдельной доставки задания."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class SyncRun:
    """Защищает поколение обхода, checkpoint и атомарный прогресс страницы."""

    id: EntityIdVO
    connection_id: EntityIdVO
    config_revision: int
    revision: int
    status: SyncRunStatus
    current_job_id: EntityIdVO
    _checkpoint: JsonObject
    processed_count: int
    skipped_count: int
    pages_count: int
    automatic: bool
    error_code: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @classmethod
    def create(
        cls,
        *,
        run_id: EntityIdVO,
        connection_id: EntityIdVO,
        config_revision: int,
        job_id: EntityIdVO,
        automatic: bool,
        now: datetime,
    ) -> "SyncRun":
        """Создаёт ещё не начатый обход без credentials и товарных данных."""
        return cls.restore(
            run_id=run_id,
            connection_id=connection_id,
            config_revision=config_revision,
            revision=1,
            status=SyncRunStatus.QUEUED,
            current_job_id=job_id,
            checkpoint={},
            processed_count=0,
            skipped_count=0,
            pages_count=0,
            automatic=automatic,
            error_code=None,
            created_at=now,
            started_at=None,
            finished_at=None,
        )

    @classmethod
    def restore(
        cls,
        *,
        run_id: EntityIdVO,
        connection_id: EntityIdVO,
        config_revision: int,
        revision: int,
        status: SyncRunStatus,
        current_job_id: EntityIdVO,
        checkpoint: JsonObject,
        processed_count: int,
        skipped_count: int,
        pages_count: int,
        automatic: bool,
        error_code: str | None,
        created_at: datetime,
        started_at: datetime | None,
        finished_at: datetime | None,
    ) -> "SyncRun":
        """Восстанавливает запуск, не исправляя противоречивую запись."""
        if (
            not all(
                isinstance(value, EntityIdVO)
                for value in (run_id, connection_id, current_job_id)
            )
            or any(
                type(value) is not int or value < 1
                for value in (config_revision, revision)
            )
            or not isinstance(status, SyncRunStatus)
            or not isinstance(checkpoint, dict)
            or type(automatic) is not bool
            or any(
                type(value) is not int or value < 0
                for value in (processed_count, skipped_count, pages_count)
            )
            or skipped_count > processed_count
            or not isinstance(created_at, datetime)
            or created_at.tzinfo is None
            or (
                started_at is not None
                and (
                    not isinstance(started_at, datetime)
                    or started_at.tzinfo is None
                    or started_at < created_at
                )
            )
            or (
                finished_at is not None
                and (
                    not isinstance(finished_at, datetime)
                    or finished_at.tzinfo is None
                    or finished_at < (started_at or created_at)
                )
            )
            or (
                status is SyncRunStatus.QUEUED
                and (
                    started_at is not None
                    or any((pages_count, processed_count, skipped_count))
                )
            )
            or (
                status in {SyncRunStatus.RUNNING, SyncRunStatus.COMPLETED}
                and started_at is None
            )
            or (
                (
                    status
                    in {
                        SyncRunStatus.COMPLETED,
                        SyncRunStatus.FAILED,
                        SyncRunStatus.CANCELLED,
                    }
                )
                != (finished_at is not None)
            )
            or (
                (status in {SyncRunStatus.FAILED, SyncRunStatus.CANCELLED})
                != (isinstance(error_code, str) and bool(error_code))
            )
            or (
                status
                in {
                    SyncRunStatus.QUEUED,
                    SyncRunStatus.RUNNING,
                    SyncRunStatus.COMPLETED,
                }
                and error_code is not None
            )
            or (isinstance(error_code, str) and len(error_code) > 100)
        ):
            raise InvalidSyncRunError("Некорректное состояние синхронизации.")
        try:
            json.dumps(checkpoint, allow_nan=False)
        except (TypeError, ValueError):
            raise InvalidSyncRunError(
                "Checkpoint должен быть JSON-документом."
            ) from None
        return cls(
            run_id,
            connection_id,
            config_revision,
            revision,
            status,
            current_job_id,
            deepcopy(checkpoint),
            processed_count,
            skipped_count,
            pages_count,
            automatic,
            error_code,
            created_at,
            started_at,
            finished_at,
        )

    @property
    def checkpoint(self) -> JsonObject:
        """Возвращает независимый снимок курсора платформы."""
        return deepcopy(self._checkpoint)

    @property
    def active(self) -> bool:
        """Определяет, может ли запуск принимать следующую страницу."""
        return self.status in {SyncRunStatus.QUEUED, SyncRunStatus.RUNNING}

    def accepts(
        self, *, job_id: EntityIdVO, config_revision: int, revision: int | None = None
    ) -> bool:
        """Отклоняет старые задания и повторно применяемые страницы."""
        return (
            self.active
            and self.current_job_id == job_id
            and self.config_revision == config_revision
            and (revision is None or self.revision == revision)
        )

    def start(self, *, now: datetime) -> None:
        """Начинает запуск; повторная попытка текущей страницы не сбрасывает его."""
        if (
            not self.active
            or not isinstance(now, datetime)
            or now.tzinfo is None
            or now < self.created_at
        ):
            raise InvalidSyncRunError("Запуск не может быть начат.")
        if self.status is SyncRunStatus.QUEUED:
            self.status = SyncRunStatus.RUNNING
            self.started_at = now
            self.revision += 1

    def apply_page(
        self,
        *,
        checkpoint: JsonObject,
        processed: int,
        skipped: int,
        next_job_id: EntityIdVO | None,
        now: datetime,
    ) -> None:
        """Продвигает курсор вместе с данными страницы либо завершает обход."""
        if (
            self.status is not SyncRunStatus.RUNNING
            or not isinstance(checkpoint, dict)
            or type(processed) is not int
            or type(skipped) is not int
            or processed < 0
            or skipped < 0
            or skipped > processed
            or (
                next_job_id is not None
                and (
                    not isinstance(next_job_id, EntityIdVO)
                    or next_job_id == self.current_job_id
                )
            )
            or not isinstance(now, datetime)
            or now.tzinfo is None
            or now < self.started_at
        ):
            raise InvalidSyncRunError("Некорректный результат страницы.")
        try:
            json.dumps(checkpoint, allow_nan=False)
        except (TypeError, ValueError):
            raise InvalidSyncRunError(
                "Checkpoint должен быть JSON-документом."
            ) from None
        self._checkpoint = deepcopy(checkpoint)
        self.processed_count += processed
        self.skipped_count += skipped
        self.pages_count += 1
        self.revision += 1
        if next_job_id is None:
            self.status = SyncRunStatus.COMPLETED
            self.finished_at = now
        else:
            self.current_job_id = next_job_id

    def fail(self, *, error_code: str, now: datetime) -> None:
        """Завершает запуск безопасным кодом без текста ответа площадки."""
        self._finish(status=SyncRunStatus.FAILED, error_code=error_code, now=now)

    def cancel(self, *, error_code: str, now: datetime) -> None:
        """Инвалидирует активный запуск при изменении подключения."""
        self._finish(status=SyncRunStatus.CANCELLED, error_code=error_code, now=now)

    def _finish(self, *, status: SyncRunStatus, error_code: str, now: datetime) -> None:
        """Проверяет завершение до изменения любого поля."""
        if (
            not self.active
            or not isinstance(error_code, str)
            or not error_code
            or len(error_code) > 100
            or not isinstance(now, datetime)
            or now.tzinfo is None
            or now < (self.started_at or self.created_at)
        ):
            raise InvalidSyncRunError("Запуск уже завершён либо причина некорректна.")
        self.status = status
        self.error_code = error_code
        self.finished_at = now
        self.revision += 1
