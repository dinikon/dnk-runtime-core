from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ImportOptions:
    """Ограничения импорта, передаваемые через composition root."""

    batch_size: int = 1000
    max_error_ratio: float = 0.5
    max_rows: int = 2_000_000
    max_download_bytes: int = 1024**3
    max_uncompressed_bytes: int = 4 * 1024**3
    batch_max_bytes: int = 4 * 1024**2
    parser_queue_batches: int = 1
    max_record_bytes: int = 1024**2
    string_cache_bytes: int = 8 * 1024**2
    max_temp_bytes: int = 4 * 1024**3
    failed_staging_retention_days: int = 7

    def __post_init__(self):
        if not 0 <= self.max_error_ratio <= 1:
            raise ValueError("max_error_ratio must be between 0 and 1.")
        for name in self.__dataclass_fields__:
            if name != "max_error_ratio" and (
                type(getattr(self, name)) is not int or getattr(self, name) < 1
            ):
                raise ValueError(f"{name} must be a positive integer.")
        if self.max_download_bytes > self.max_temp_bytes:
            raise ValueError("Download budget exceeds temporary storage budget.")


__all__ = ["ImportOptions"]
