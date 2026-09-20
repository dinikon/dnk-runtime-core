from pydantic import BaseModel, Field


class DeletePriceListRequest(BaseModel):
    """HTTP-входные поля DeletePriceListRequest."""

    confirmation_title: str = Field(min_length=1, max_length=255)


__all__ = ["DeletePriceListRequest"]
