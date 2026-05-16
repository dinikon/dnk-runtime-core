from pydantic import BaseModel

from .company_response import CompanyResponseSchema


class ListCompaniesResponseSchema(BaseModel):
    """Pydantic-схема HTTP-ответа со страницей компаний."""

    items: list[CompanyResponseSchema]
    limit: int
    offset: int
    count: int


__all__ = ["ListCompaniesResponseSchema"]
