from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.modules.communication.application.provider_connection import (
    CreateProviderConnectionCommand,
)
from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
from src.modules.communication.presentation.depends.application import (
    CreateProviderConnectionUseCaseDep,
    ListProviderConnectionsUseCaseDep,
)
from src.modules.communication.presentation.http.common import require_tenant_id
from src.modules.runtime_data import (
    RuntimeDataFilterError,
    RuntimeDataPersistenceError,
    RuntimeDataPolicyError,
    RuntimeDataValidationError,
)
from src.modules.schema_registry.domain.error import (
    RuntimeObjectDescriptorError,
    RuntimeObjectNotFoundError,
    SchemaRegistryMetadataInconsistentError,
)
from src.modules.shared.depends import AuthenticatedRequestContextDep
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/communication/providers", tags=["communication"])


class CreateProviderConnectionRequestSchema(BaseModel):
    provider_connector_id: UUID
    connection_code: str
    connection_name: str
    channel_code: str
    config: dict[str, Any] = Field(default_factory=dict)
    secrets: dict[str, Any] = Field(default_factory=dict)
    secret_ref: str | None = None


class ProviderConnectionResponseSchema(BaseModel):
    provider_connection_id: UUID
    tenant_id: UUID
    provider_connector_id: UUID
    connection_code: str
    connection_name: str
    channel_code: str
    config: dict[str, Any]
    secret_ref: str | None
    has_secrets: bool
    status: str
    created_at: datetime
    updated_at: datetime


class ListProviderConnectionsResponseSchema(BaseModel):
    items: list[ProviderConnectionResponseSchema]


@router.post(
    "/connections",
    response_model=ProviderConnectionResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_provider_connection(
    payload: CreateProviderConnectionRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: CreateProviderConnectionUseCaseDep,
) -> ProviderConnectionResponseSchema:
    tenant_id = require_tenant_id(context)
    try:
        result = await use_case(
            CreateProviderConnectionCommand(
                tenant_id=tenant_id,
                provider_connector_id=payload.provider_connector_id,
                connection_code=payload.connection_code,
                connection_name=payload.connection_name,
                channel_code=payload.channel_code,
                config=payload.config,
                secrets=payload.secrets,
                secret_ref=payload.secret_ref,
            )
        )
    except CommunicationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (
        RuntimeDataPersistenceError,
        RuntimeDataPolicyError,
        RuntimeObjectDescriptorError,
        RuntimeObjectNotFoundError,
        SchemaRegistryMetadataInconsistentError,
        CommunicationRuntimeStateError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except (
        CommunicationValidationError,
        RuntimeDataValidationError,
        RuntimeDataFilterError,
        DomainError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return ProviderConnectionResponseSchema(
        provider_connection_id=result.provider_connection_id,
        tenant_id=result.tenant_id,
        provider_connector_id=result.provider_connector_id,
        connection_code=result.connection_code,
        connection_name=result.connection_name,
        channel_code=result.channel_code,
        config=dict(result.config),
        secret_ref=result.secret_ref,
        has_secrets=result.has_secrets,
        status=result.status,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.get(
    "/connections",
    response_model=ListProviderConnectionsResponseSchema,
)
async def list_provider_connections(
    context: AuthenticatedRequestContextDep,
    use_case: ListProviderConnectionsUseCaseDep,
) -> ListProviderConnectionsResponseSchema:
    tenant_id = require_tenant_id(context)
    try:
        items = await use_case(tenant_id)
    except CommunicationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (
        RuntimeDataPersistenceError,
        RuntimeDataPolicyError,
        RuntimeObjectDescriptorError,
        RuntimeObjectNotFoundError,
        SchemaRegistryMetadataInconsistentError,
        CommunicationRuntimeStateError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except (
        CommunicationValidationError,
        RuntimeDataValidationError,
        RuntimeDataFilterError,
        DomainError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return ListProviderConnectionsResponseSchema(
        items=[
            ProviderConnectionResponseSchema(
                provider_connection_id=item.provider_connection_id,
                tenant_id=item.tenant_id,
                provider_connector_id=item.provider_connector_id,
                connection_code=item.connection_code,
                connection_name=item.connection_name,
                channel_code=item.channel_code,
                config=dict(item.config),
                secret_ref=item.secret_ref,
                has_secrets=item.has_secrets,
                status=item.status,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in items
        ]
    )


__all__ = [
    "CreateProviderConnectionRequestSchema",
    "ListProviderConnectionsResponseSchema",
    "ProviderConnectionResponseSchema",
    "create_provider_connection",
    "list_provider_connections",
    "router",
]
