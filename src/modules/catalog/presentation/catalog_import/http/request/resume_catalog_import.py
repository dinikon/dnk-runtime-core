from pydantic import BaseModel, ConfigDict, Field


class ResumeCatalogImportRequest(BaseModel):
    """Поколение остановки, подтверждённое пользователем для безопасного повтора."""

    model_config = ConfigDict(extra="forbid")
    generation: int = Field(ge=0, strict=True)
