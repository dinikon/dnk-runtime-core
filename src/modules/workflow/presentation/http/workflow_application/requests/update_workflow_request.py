from pydantic import BaseModel


class UpdateWorkflowRequestSchema(BaseModel):
    """Pydantic-схема тела запроса обновления workflow."""

    title: str
    description: str | None = None
    icon: str
    icon_background: str


__all__ = ["UpdateWorkflowRequestSchema"]
