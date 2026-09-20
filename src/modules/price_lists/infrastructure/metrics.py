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

price_list_sync_phase_duration = Histogram(
    "price_list_sync_phase_duration_seconds",
    "Import phase duration.",
    ["phase", "format"],
)


class PrometheusImportObserver:
    """Адаптер метрик с ограниченной кардинальностью labels."""

    def phase(self, name, source_format, seconds):
        price_list_sync_phase_duration.labels(phase=name, format=source_format).observe(
            seconds
        )

    def completed(self, source_format, trigger, status, counters, seconds):
        price_list_sync_runs.labels(
            status=status, format=source_format, trigger=trigger
        ).inc()
        price_list_sync_duration.labels(format=source_format).observe(seconds)
        for name, value in counters.items():
            price_list_sync_rows.labels(result=name).inc(value)

    def downloaded(self, source_format, size):
        price_list_sync_download_bytes.labels(format=source_format).inc(size)
