from pydantic import BaseModel, ConfigDict, Field


class ResumeConnectionRequest(BaseModel):
    """Принимает поля HTTP-сценария resume_connection без tenant/actor из body."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    revision: int = Field(ge=1)
