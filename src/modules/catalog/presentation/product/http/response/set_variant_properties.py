from uuid import UUID
from pydantic import BaseModel


class SetVariantPropertiesResponse(BaseModel):
    """Ответ HTTP-сценария set_variant_properties."""

    id: UUID
    revision: int
