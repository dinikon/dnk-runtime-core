from src.modules.communication.presentation.http.provider_connection.responses.provider_connection_response import (
    ProviderConnectionResponseSchema,
)

from pydantic import BaseModel


class ListProviderConnectionsResponseSchema(BaseModel):
    """Pydantic-схема HTTP-ответа списка provider connections."""

    items: list[ProviderConnectionResponseSchema]


__all__ = ["ListProviderConnectionsResponseSchema"]
