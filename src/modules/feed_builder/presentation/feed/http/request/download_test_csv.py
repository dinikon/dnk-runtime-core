from pydantic import BaseModel, ConfigDict, Field


class DownloadTestCsvRequest(BaseModel):
    """Фиксирует версию сохранённых настроек и схемы пробного CSV."""

    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(strict=True, ge=1, le=2**63 - 1)
