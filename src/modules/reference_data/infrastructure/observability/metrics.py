from prometheus_client import Counter, Gauge

reference_data_sync_total = Counter(
    "reference_data_sync_total",
    "Reference catalog synchronization attempts",
    ("dataset", "result"),
)
reference_data_last_success_timestamp = Gauge(
    "reference_data_last_success_timestamp_seconds",
    "Timestamp of the last successful reference catalog synchronization",
    ("dataset",),
)
