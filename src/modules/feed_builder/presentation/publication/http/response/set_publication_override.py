from pydantic import BaseModel


class SetPublicationOverrideResponse(BaseModel):
    """Передаёт актуальную версию публикации после изменения поля."""

    publication_version: int
