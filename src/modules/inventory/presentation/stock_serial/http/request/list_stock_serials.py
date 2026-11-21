from pydantic import BaseModel, ConfigDict, Field, StrictStr


class ListStockSerialsRequest(BaseModel):
    """Проверяет поиск и границы серверной пагинации серийных экземпляров."""

    model_config = ConfigDict(extra="forbid")
    offset: int = Field(default=0, ge=0, le=2147483647)
    limit: int = Field(default=50, ge=1, le=100)
    search: StrictStr | None = None
