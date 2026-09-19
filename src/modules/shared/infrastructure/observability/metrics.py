from prometheus_client import Counter, Gauge, Histogram

mtls_rejections = Counter(
    "dnk_runtime_mtls_rejections_total",
    "Rejected management connections before proxy normalization.",
    ["reason"],
)
oidc_errors = Counter(
    "dnk_runtime_oidc_errors_total",
    "Cloud authorization failures without sensitive provider details.",
    ["reason"],
)

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
