from pydantic import BaseModel


class ResetPublicationOverrideResponse(BaseModel):
    """Передаёт актуальную версию публикации после изменения поля."""

    publication_version: int
