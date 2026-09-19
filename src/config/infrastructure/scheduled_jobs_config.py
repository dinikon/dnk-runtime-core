from __future__ import annotations

from pydantic import BaseModel, Field, PositiveInt
from pydantic_settings import BaseSettings


class ScheduledJobsSettings(BaseModel):
    """Shared scheduled jobs worker settings."""

    process_limit: PositiveInt = Field(
        default=100,
        description="Default due scheduled jobs batch size.",
    )
    recover_limit: PositiveInt = Field(
        default=100,
        description="Default stuck scheduled jobs recovery batch size.",
    )
    lock_ttl_seconds: PositiveInt = Field(
        default=300,
        description="Worker lock TTL in seconds for claimed scheduled jobs.",
    )
    retry_base_seconds: PositiveInt = Field(
        default=30,
        description="Base seconds for linear scheduled job retry backoff.",
    )
    max_attempts: PositiveInt = Field(
        default=5,
        description="Maximum attempts before scheduled job is failed.",
    )
    poll_interval_seconds: PositiveInt = Field(
        default=2,
        description="Seconds between due-job polls when the queue is idle.",
    )
    recover_interval_seconds: PositiveInt = Field(
        default=30,
        description="Seconds between expired lease recovery passes.",
    )
    lock_heartbeat_seconds: PositiveInt = Field(
        default=60,
        description="Seconds between lease extensions for a running job.",
    )
    shutdown_grace_seconds: PositiveInt = Field(
        default=60,
        description="Grace period used by process supervisors during shutdown.",
    )
    heartbeat_path: str = Field(
        default="/tmp/dnk-cron-worker-heartbeat",
        description="Worker heartbeat file used by container health checks.",
    )


class ScheduledJobsConfig(BaseSettings):
    """Config group for the shared scheduled jobs foundation."""

    SCHEDULED_JOBS: ScheduledJobsSettings = Field(
        default_factory=ScheduledJobsSettings,
        description="Shared scheduled jobs settings.",
    )


__all__ = [
    "ScheduledJobsConfig",
    "ScheduledJobsSettings",
]
