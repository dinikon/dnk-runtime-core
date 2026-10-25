from pydantic import BaseModel, ConfigDict, Field


class StartCatalogImportRequest(BaseModel):
    """Версия предпросмотра, явно подтверждённая пользователем."""

    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)
