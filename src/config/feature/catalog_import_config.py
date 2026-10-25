from typing import Self
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings


class CatalogImportSettings(BaseModel):
    """Ограничения потокового импорта и сроков хранения."""

    model_config = ConfigDict(validate_default=True)

    max_active_per_tenant: int = Field(default=1, ge=1)
    source_max_bytes: int = Field(default=100 * 1024 * 1024, gt=0)
    max_records: int = Field(default=100_000, gt=0)
    max_images: int = Field(default=100, ge=1, le=100)
    image_max_bytes: int = Field(default=10 * 1024 * 1024, gt=0, le=10 * 1024 * 1024)
    download_concurrency: int = Field(default=4, ge=1, le=16)
    download_timeout_seconds: int = Field(default=300, gt=0)
    batch_size: int = Field(default=100, ge=1, le=1000)
    batch_seconds: int = Field(default=60, ge=1)
    draft_hours: int = Field(default=24, gt=0)
    source_days: int = Field(default=7, gt=0)
    result_days: int = Field(default=30, gt=0)

    @model_validator(mode="after")
    def validate_retention(self) -> Self:
        """Не допускает удаления журнала раньше очистки исходного файла."""
        if self.result_days < self.source_days:
            raise ValueError("result_days must be at least source_days")
        return self


class CatalogImportConfig(BaseSettings):
    """Подключает настройки импорта к общему Config."""

    CATALOG_IMPORT: CatalogImportSettings = Field(default_factory=CatalogImportSettings)
