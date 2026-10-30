from pydantic import BaseModel, ConfigDict, Field


class RequestContentReconciliationRequest(BaseModel):
    """Защищает запуск сверки от изменения состояния после чтения Console."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    expected_revision: int = Field(gt=0, strict=True)
