from pydantic import BaseModel, ConfigDict, Field


class ListPackagingTypesRequest(BaseModel):
    """Проверяет параметры HTTP-списка, сохраняя явный false фильтра активности."""

    model_config = ConfigDict(extra="forbid")
    offset: int = Field(default=0, ge=0, le=2_147_483_647)
    limit: int = Field(default=50, ge=1, le=100)
    search: str | None = None
    is_active: bool | None = None
