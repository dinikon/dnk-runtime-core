from prometheus_client import Counter, Gauge, Histogram

scheduled_job_worker_polls = Counter(
    "scheduled_job_worker_poll_total",
    "Scheduled job worker polling cycles.",
    ["result"],
)
scheduled_job_worker_cycles = Histogram(
    "scheduled_job_worker_cycle_duration_seconds",
    "Scheduled job worker poll and recovery cycle duration.",
    ["phase"],
)
scheduled_job_worker_heartbeat = Gauge(
    "scheduled_job_worker_heartbeat_timestamp_seconds",
    "Unix timestamp of the most recent healthy worker cycle.",
)
