from uuid import UUID
from pydantic import BaseModel, ConfigDict


class StartPublicationInitializationRequest(BaseModel):
    """Принимает поля HTTP-сценария start_publication_initialization без tenant/actor из body."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    request_key: UUID
