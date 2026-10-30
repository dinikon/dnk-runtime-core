from pydantic import BaseModel, ConfigDict, Field


class ResolveContentUncertaintyRequest(BaseModel):
    """Защищает ручное завершение ревизией и явным признанием неопределённости."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    expected_revision: int = Field(gt=0, strict=True)
    acknowledge_unconfirmed: bool = Field(strict=True)
