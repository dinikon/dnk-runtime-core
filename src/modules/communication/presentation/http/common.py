from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
from src.modules.runtime_data.domain.error import (
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
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.domain.identity_context import RequestContext


def require_tenant_id(context: RequestContext) -> UUID:
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
    return principal.tenant_id


def map_communication_http_error(exc: Exception) -> HTTPException:
    """Мапит communication domain/runtime ошибки в HTTPException."""
    if isinstance(exc, CommunicationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(
        exc,
        (
            RuntimeDataPersistenceError,
            RuntimeDataPolicyError,
            RuntimeObjectDescriptorError,
            RuntimeObjectNotFoundError,
            SchemaRegistryMetadataInconsistentError,
            CommunicationRuntimeStateError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(
        exc,
        (
            CommunicationValidationError,
            RuntimeDataValidationError,
            RuntimeDataFilterError,
            DomainError,
        ),
    ):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    raise exc


__all__ = ["map_communication_http_error", "require_tenant_id"]
