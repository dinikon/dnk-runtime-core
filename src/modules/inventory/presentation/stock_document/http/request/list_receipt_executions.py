from pydantic import BaseModel,ConfigDict,Field
class ListReceiptExecutionsRequest(BaseModel):
    """Проверяет транспортную страницу истории."""
    model_config=ConfigDict(extra="forbid")
    offset:int=Field(default=0,ge=0)
    limit:int=Field(default=20,ge=1,le=100)
