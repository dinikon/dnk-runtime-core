"""Явное восстановление запуска через Domain-фабрику."""

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.sync_run.aggregate import SyncRun, SyncRunStatus
from src.modules.channels.domain.sync_run.error import InvalidSyncRunError
from src.modules.channels.infrastructure.persistence.models.sync_run import SyncRunModel


def to_domain(row: SyncRunModel) -> SyncRun:
    """Передаёт проверки сохранённого состояния Domain."""
    if row.checkpoint_version != 1:
        raise InvalidSyncRunError("Версия checkpoint не поддерживается.")
    try:
        status = SyncRunStatus(row.status)
    except ValueError:
        raise InvalidSyncRunError("Неизвестное состояние запуска.") from None
    return SyncRun.restore(
        run_id=EntityIdVO.from_value(row.id),
        connection_id=EntityIdVO.from_value(row.connection_id),
        config_revision=row.config_revision,
        revision=row.revision,
        status=status,
        current_job_id=EntityIdVO.from_value(row.current_job_id),
        checkpoint=row.checkpoint,
        processed_count=row.processed_count,
        skipped_count=row.skipped_count,
        pages_count=row.pages_count,
        automatic=row.automatic,
        error_code=row.error_code,
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )


def to_values(run: SyncRun) -> dict[str, object]:
    """Извлекает поля без SQL, commit и проверки бизнес-правил."""
    return {
        "id": run.id.uuid,
        "connection_id": run.connection_id.uuid,
        "config_revision": run.config_revision,
        "revision": run.revision,
        "status": run.status.value,
        "current_job_id": run.current_job_id.uuid,
        "checkpoint_version": 1,
        "checkpoint": run.checkpoint,
        "processed_count": run.processed_count,
        "skipped_count": run.skipped_count,
        "pages_count": run.pages_count,
        "automatic": run.automatic,
        "error_code": run.error_code,
        "created_at": run.created_at,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
    }
