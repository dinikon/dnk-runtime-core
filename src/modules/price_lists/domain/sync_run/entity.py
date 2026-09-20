from dataclasses import dataclass, field
from datetime import datetime
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.domain.sync_run.value_object import SyncRunIdVO
from src.modules.price_lists.domain.sync_run.error import SourceValidationError


@dataclass(slots=True)
class SyncRun:
    """Запуск импорта, итоговые счётчики и защита повторной публикации."""

    id: SyncRunIdVO
    price_list_id: PriceListIdVO
    scheduled_job_id: EntityIdVO | None
    status: str
    trigger: str
    planned_at: datetime | None
    started_at: datetime
    finished_at: datetime | None = None
    source_checksum: str | None = None
    counters: dict[str, int] = field(default_factory=dict)
    error_summary: str | None = None

    @classmethod
    def create(cls, run_id, price_list_id, job_id, trigger, planned_at, now):
        """Начинает загрузку источника для одной scheduled job."""
        return cls(
            run_id, price_list_id, job_id, "downloading", trigger, planned_at, now
        )

    @property
    def published(self):
        """Показывает, что повтор не должен применять данные."""
        return self.status in ("succeeded", "partial", "skipped")

    def reset(self, now):
        """Начинает новую попытку после удаления старого staging."""
        self.status = "downloading"
        self.started_at = now
        self.finished_at = None
        self.source_checksum = None
        self.counters = {}
        self.error_summary = None

    def validate(self, max_error_ratio: float):
        """Проверяет весь источник до публикации."""
        read = self.counters.get("read", 0)
        rejected = self.counters.get("rejected", 0)
        if not read or read == rejected or rejected > read * max_error_ratio:
            raise SourceValidationError("Source validation threshold exceeded.")

    def finish(self, now, *, error: str | None = None):
        """Завершает публикацию или фиксирует безопасное сообщение ошибки."""
        self.finished_at = now
        self.error_summary = error
        self.status = (
            "failed"
            if error
            else ("partial" if self.counters.get("rejected") else "succeeded")
        )


__all__ = ["SyncRun"]
