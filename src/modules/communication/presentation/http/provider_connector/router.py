from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.modules.communication.application.provider_connector import (
    RegisterProviderConnectorCommand,
)
from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
from src.modules.communication.presentation.depends.application import (
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


__all__ = [
    "ImportYamlRequestSchema",
    "ListProviderConnectorsResponseSchema",
    "ProviderConnectorResponseSchema",
    "ProviderMessageTypeResponseSchema",
    "router",
]
