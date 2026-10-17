from pydantic import BaseModel, ConfigDict, Field


class UploadCatalogItemImageRequest(BaseModel):
    """Проверяемые поля multipart загрузки, отдельно от бинарного file stream."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    main: bool = False
    alt: str = Field(default="", max_length=1000)
    caption: str = Field(default="", max_length=5000)
