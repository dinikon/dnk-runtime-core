from pydantic import BaseModel, ConfigDict, Field, StrictInt


class CancelIssueDocumentRequest(BaseModel):
    """Проверяет транспортную форму действия и обязательную ожидаемую версию."""

    model_config = ConfigDict(extra="forbid")
    expected_version: StrictInt = Field(ge=0)
