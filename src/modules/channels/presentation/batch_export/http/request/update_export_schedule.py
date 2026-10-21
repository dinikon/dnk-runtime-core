from pydantic import BaseModel, ConfigDict, Field


class UpdateExportScheduleRequest(BaseModel):
    """Ограничивает пользовательские параметры ежедневного запуска."""

    model_config = ConfigDict(extra="forbid", strict=True)
    enabled: bool
    hour: int = Field(ge=0, le=23)
    minute: int = Field(ge=0, le=59)
    timezone: str = Field(min_length=1, max_length=100)
    expected_revision: int = Field(ge=1)
