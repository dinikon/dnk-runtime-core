from pydantic import BaseModel, ConfigDict, Field


class UploadCatalogVariantImageRequest(BaseModel):
    """Проверяемые поля multipart загрузки, отдельно от бинарного file stream."""

    model_config = ConfigDict(extra="forbid")

    main: bool = False
    alt: str = Field(default="", max_length=1000)
    caption: str = Field(default="", max_length=5000)
