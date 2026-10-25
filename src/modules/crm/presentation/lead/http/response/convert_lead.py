from pydantic import BaseModel


class ConvertLeadResponse(BaseModel):
    """Только действительно созданные результаты конвертации."""

    conversion_id: str
    mode: str
    contact_id: str | None
    company_id: str | None
    deal_id: str | None
    basket_id: str | None
    converted_at: str
    converted_by: str
    replay: bool
