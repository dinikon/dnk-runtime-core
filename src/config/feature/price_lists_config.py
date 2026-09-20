from __future__ import annotations

import base64
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator
from pydantic_settings import BaseSettings


class PriceListsSettings(BaseModel):
    """Secrets and safety limits for partner price-list sources."""

    model_config = ConfigDict(hide_input_in_errors=True)
    source_encryption_key: str = Field(default="", repr=False)
    encryption_key_path: str = ""

    batch_size: PositiveInt = 1000
    max_error_ratio: float = Field(default=0.5, ge=0, le=1)
    max_rows: PositiveInt = 2_000_000
    max_download_bytes: PositiveInt = 1024**3
    max_uncompressed_bytes: PositiveInt = 4 * 1024**3
    batch_max_bytes: PositiveInt = 4 * 1024**2
    parser_queue_batches: PositiveInt = 1
    max_record_bytes: PositiveInt = 1024**2
    string_cache_bytes: PositiveInt = 8 * 1024**2
    max_temp_bytes: PositiveInt = 4 * 1024**3
    failed_staging_retention_days: PositiveInt = 7

    @model_validator(mode="after")
    def load_and_validate_key(self):
        if self.source_encryption_key and self.encryption_key_path:
            raise ValueError(
                "Use PRICE_LISTS source_encryption_key OR encryption_key_path."
            )
        if self.encryption_key_path:
            try:
                self.source_encryption_key = (
                    Path(self.encryption_key_path).read_text(encoding="utf-8").strip()
                )
            except OSError:
                raise ValueError(
                    "Cannot read Price Lists encryption key file."
                ) from None
        if self.source_encryption_key:
            try:
                valid = len(base64.urlsafe_b64decode(self.source_encryption_key)) == 32
            except (TypeError, ValueError):
                valid = False
            if not valid:
                raise ValueError("Price Lists encryption key must be a Fernet key.")
        if self.max_download_bytes > self.max_temp_bytes:
            raise ValueError("Download budget exceeds temporary storage budget.")
        return self


class PriceListsConfig(BaseSettings):
    PRICE_LISTS: PriceListsSettings = Field(default_factory=PriceListsSettings)


__all__ = ["PriceListsConfig", "PriceListsSettings"]
