from __future__ import annotations

from fastapi import HTTPException, status

from src.modules.communication.domain.error import (
    CommunicationNotFoundError,
    CommunicationRuntimeStateError,
    CommunicationValidationError,
)
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
from src.modules.shared.domain.errors import DomainError


def map_outbound_http_error(exc: Exception) -> HTTPException:
    """Мапит domain/runtime ошибки outbound controller в HTTPException."""
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


__all__ = ["map_outbound_http_error"]
