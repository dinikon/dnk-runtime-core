from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.modules.communication.application.provider import (
    CreateProviderConnectionCommand,
    RegisterProviderConnectorCommand,
)
from src.modules.communication.domain import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
from src.modules.communication.presentation.depends.application import (
    CreateProviderConnectionUseCaseDep,
    ListProviderConnectionsUseCaseDep,
    ListProviderConnectorsUseCaseDep,
    RegisterProviderConnectorUseCaseDep,
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


class ImportYamlRequestSchema(BaseModel):
    yaml_content: str


class ProviderConnectorResponseSchema(BaseModel):
    provider_connector_id: UUID
    provider_code: str
    provider_name: str
    version: str
    connector_type: str
    channels: list[str]
    config_schema: dict[str, Any]
    secrets_schema: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime


class ProviderMessageTypeResponseSchema(BaseModel):
    provider_message_type_id: UUID
    provider_connector_id: UUID
    message_type_code: str
    channel_code: str
    name: str
    field_schema: dict[str, Any]
    ui_schema: dict[str, Any]
    is_active: bool


class ListProviderConnectorsResponseSchema(BaseModel):
    connectors: list[ProviderConnectorResponseSchema]
    message_types: list[ProviderMessageTypeResponseSchema]


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
    "/connectors/import-yaml",
    response_model=ProviderConnectorResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def import_provider_connector_yaml(
    payload: ImportYamlRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: RegisterProviderConnectorUseCaseDep,
) -> ProviderConnectorResponseSchema:
    tenant_id = require_tenant_id(context)
    try:
        result = await use_case(
            RegisterProviderConnectorCommand(
                tenant_id=tenant_id,
                yaml_content=payload.yaml_content,
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
    return ProviderConnectorResponseSchema(
        provider_connector_id=result.provider_connector_id,
        provider_code=result.provider_code,
        provider_name=result.provider_name,
        version=result.version,
        connector_type=result.connector_type,
        channels=list(result.channels),
        config_schema=dict(result.config_schema),
        secrets_schema=dict(result.secrets_schema),
        status=result.status,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.get(
    "/connectors",
    response_model=ListProviderConnectorsResponseSchema,
)
async def list_provider_connectors(
    context: AuthenticatedRequestContextDep,
    use_case: ListProviderConnectorsUseCaseDep,
) -> ListProviderConnectorsResponseSchema:
    tenant_id = require_tenant_id(context)
    try:
        connectors, message_types = await use_case(tenant_id)
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
    return ListProviderConnectorsResponseSchema(
        connectors=[
            ProviderConnectorResponseSchema(
                provider_connector_id=item.provider_connector_id,
                provider_code=item.provider_code,
                provider_name=item.provider_name,
                version=item.version,
                connector_type=item.connector_type,
                channels=list(item.channels),
                config_schema=dict(item.config_schema),
                secrets_schema=dict(item.secrets_schema),
                status=item.status,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in connectors
        ],
        message_types=[
            ProviderMessageTypeResponseSchema(
                provider_message_type_id=item.provider_message_type_id,
                provider_connector_id=item.provider_connector_id,
                message_type_code=item.message_type_code,
                channel_code=item.channel_code,
                name=item.name,
                field_schema=dict(item.field_schema),
                ui_schema=dict(item.ui_schema),
                is_active=item.is_active,
            )
            for item in message_types
        ],
    )


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
    "ImportYamlRequestSchema",
    "ListProviderConnectionsResponseSchema",
    "ListProviderConnectorsResponseSchema",
    "ProviderConnectionResponseSchema",
    "ProviderConnectorResponseSchema",
    "ProviderMessageTypeResponseSchema",
    "router",
]
