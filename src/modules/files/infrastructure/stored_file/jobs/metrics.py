from datetime import datetime
from uuid import UUID
from prometheus_client import Counter, Gauge, Histogram
from src.modules.files.application.stored_file.command.cleanup_expired_trash.dto import (
    CleanupExpiredTrashBacklogDTO,
)

trash_backlog_files = Gauge(
    "files_trash_backlog_files",
    "Last committed trash scan: files by tenant and state.",
    ["tenant_id", "state"],
)
trash_backlog_bytes = Gauge(
    "files_trash_backlog_bytes",
    "Last committed trash scan: bytes by tenant and state.",
    ["tenant_id", "state"],
)
trash_max_delay = Gauge(
    "files_trash_max_purge_delay_seconds",
    "Delay of oldest overdue unpurged file at last committed scan.",
    ["tenant_id"],
)
trash_queued = Counter(
    "files_trash_queued_total",
    "Committed file purge requests from trash scans.",
    ["kind"],
)
purge_deliveries = Counter(
    "files_purge_deliveries_total", "File purge worker delivery outcomes.", ["outcome"]
)
purge_duration = Histogram(
    "files_purge_duration_seconds",
    "File purge delivery duration including admission and commit.",
)


def observe_backlog(
    tenant_id: UUID, snapshot: CleanupExpiredTrashBacklogDTO, now: datetime
) -> None:
    """Публикует снимок только после commit; labels содержат внутренний tenant ID."""
    tenant = str(tenant_id)
    trash_backlog_files.labels(tenant, "expired").set(snapshot.expired_count)
    trash_backlog_bytes.labels(tenant, "expired").set(snapshot.expired_size_bytes)
    trash_backlog_files.labels(tenant, "pending").set(snapshot.pending_count)
    trash_backlog_bytes.labels(tenant, "pending").set(snapshot.pending_size_bytes)
    delay = (
        max(0, (now - snapshot.oldest_purge_after).total_seconds())
        if snapshot.oldest_purge_after
        else 0
    )
    trash_max_delay.labels(tenant).set(delay)
