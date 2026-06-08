from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.contact_point.application.command import DetachContactPointCommand
from src.modules.contact_point.domain.binding import (
    ContactPointBindingIdVO,
    ContactPointBindingNotFoundError,
)
from src.modules.contact_point.presentation.depends.application import (
    DetachContactPointUseCaseDep,
)
from src.modules.contact_point.presentation.http.requests import (
    DetachContactPointRequestSchema,
)
from src.modules.contact_point.presentation.http.responses import (
    DetachContactPointResponseSchema,
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
from src.modules.shared import EntityIdVO
from src.modules.shared.presentation import AuthenticatedRequestContextDep
from src.modules.shared import DomainError

router = APIRouter(prefix="/contact-points", tags=["contact-points"])


@router.post(
    "/detach",
    response_model=DetachContactPointResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def detach_contact_point(
    payload: DetachContactPointRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: DetachContactPointUseCaseDep,
) -> DetachContactPointResponseSchema:
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            DetachContactPointCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                binding_id=ContactPointBindingIdVO.from_value(payload.binding_id),
            )
        )
    except (ContactPointBindingNotFoundError, RuntimeObjectNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (
        RuntimeDataPersistenceError,
        RuntimeDataPolicyError,
        RuntimeObjectDescriptorError,
        SchemaRegistryMetadataInconsistentError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (RuntimeDataValidationError, RuntimeDataFilterError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except DomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return DetachContactPointResponseSchema(
        contact_point_id=result.contact_point_id,
        binding_id=result.binding_id,
        binding_deleted=result.binding_deleted,
        contact_point_deleted=result.contact_point_deleted,
        contact_point_left_orphan=result.contact_point_left_orphan,
    )


__all__ = ["router"]
