from pydantic import BaseModel


class CreateWorkflowRequestSchema(BaseModel):
    """Pydantic-схема тела запроса создания workflow."""

    title: str
    description: str | None = None
    icon: str
    icon_background: str


__all__ = ["CreateWorkflowRequestSchema"]
