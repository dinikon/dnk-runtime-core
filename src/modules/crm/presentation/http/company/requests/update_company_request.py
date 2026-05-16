from pydantic import BaseModel


class UpdateCompanyRequestSchema(BaseModel):
    """Pydantic-схема тела запроса обновления компании."""

    legal_name: str


__all__ = ["UpdateCompanyRequestSchema"]
