from pydantic import BaseModel

from src.modules.communication.presentation.http.provider_connector.responses.provider_connector_response import (
    ProviderConnectorResponseSchema,
)
from src.modules.communication.presentation.http.provider_connector.responses.provider_message_type_response import (
    ProviderMessageTypeResponseSchema,
)


class ListProviderConnectorsResponseSchema(BaseModel):
    """Pydantic-схема HTTP-ответа списка provider connectors."""

    connectors: list[ProviderConnectorResponseSchema]
    message_types: list[ProviderMessageTypeResponseSchema]


__all__ = ["ListProviderConnectorsResponseSchema"]
