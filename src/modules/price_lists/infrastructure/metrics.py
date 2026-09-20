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


price_list_sync_batch_rows = Histogram(
    "price_list_sync_batch_rows",
    "Rows per bounded import batch.",
    ["phase", "format"],
    buckets=(1, 10, 100, 500, 1000, 2000, 5000, 10000),
)


class PrometheusImportObserver:
    """Адаптер метрик с ограниченной кардинальностью labels."""

    def batch(self, phase, source_format, rows):
        """Измеряет пакеты без tenant/job labels."""
        price_list_sync_batch_rows.labels(phase=phase, format=source_format).observe(
            rows
        )

    def phase(self, name, source_format, seconds):
        """Измеряет длительность этапа импорта."""
        price_list_sync_phase_duration.labels(phase=name, format=source_format).observe(
            seconds
        )

    def completed(self, source_format, trigger, status, counters, seconds):
        """Записывает итоговые счётчики запуска."""
        price_list_sync_runs.labels(
            status=status, format=source_format, trigger=trigger
        ).inc()
        price_list_sync_duration.labels(format=source_format).observe(seconds)
        for name, value in counters.items():
            price_list_sync_rows.labels(result=name).inc(value)

    def downloaded(self, source_format, size):
        """Учитывает объём скачанного источника."""
        price_list_sync_download_bytes.labels(format=source_format).inc(size)
