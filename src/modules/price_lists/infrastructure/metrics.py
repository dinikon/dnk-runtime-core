from prometheus_client import Counter, Histogram

price_list_sync_runs = Counter(
    "price_list_sync_runs_total",
    "Partner price-list synchronization runs.",
    ["status", "format", "trigger"],
)
price_list_sync_duration = Histogram(
    "price_list_sync_duration_seconds",
    "Partner price-list synchronization duration.",
    ["format"],
)
price_list_sync_rows = Counter(
    "price_list_sync_rows_total",
    "Partner price-list rows by synchronization result.",
    ["result"],
)
price_list_sync_download_bytes = Counter(
    "price_list_sync_download_bytes_total",
    "Downloaded partner price-list bytes.",
    ["format"],
)

__all__ = [
    "price_list_sync_download_bytes",
    "price_list_sync_duration",
    "price_list_sync_rows",
    "price_list_sync_runs",
]
