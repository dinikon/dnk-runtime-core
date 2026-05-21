from pydantic import BaseModel


class CreateCompanyRequestSchema(BaseModel):
    """Pydantic-схема тела запроса создания компании."""

    legal_name: str


__all__ = ["CreateCompanyRequestSchema"]
