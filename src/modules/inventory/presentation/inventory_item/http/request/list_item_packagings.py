from pydantic import BaseModel, ConfigDict, Field


class ListItemPackagingsRequest(BaseModel):
    """Проверяет параметры страницы и буквального поиска упаковок товара."""

    model_config = ConfigDict(extra="forbid")
    offset: int = Field(default=0, ge=0, le=2_147_483_647)
    limit: int = Field(default=50, ge=1, le=100)
    search: str | None = None
