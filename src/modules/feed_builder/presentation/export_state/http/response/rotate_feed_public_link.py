from pydantic import BaseModel


class RotateFeedPublicLinkResponse(BaseModel):
    """Возвращает новый адрес и версию Feed."""

    url: str
    feed_version: int
