from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.contact_point.application.command import AttachContactPointCommand
from src.modules.contact_point.domain.binding import ContactPointOwnerNotFoundError
from src.modules.contact_point.domain.contact_point import (
    ContactPointValidationError,
)
from src.modules.contact_point.presentation.depends.application import (
    AttachContactPointUseCaseDep,
)
from src.modules.contact_point.presentation.http.requests import (
    AttachContactPointRequestSchema,
)
from src.modules.contact_point.presentation.http.responses import (
    AttachContactPointResponseSchema,
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
from src.modules.schema_registry.domain.object_feature import (
    ObjectFeatureConfigNotFoundError,
    ObjectFeatureNotEnabledError,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.presentation import AuthenticatedRequestContextDep
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/contact-points", tags=["contact-points"])


@router.post(
    "/attach",
    response_model=AttachContactPointResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def attach_contact_point(
    payload: AttachContactPointRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: AttachContactPointUseCaseDep,
) -> AttachContactPointResponseSchema:
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            AttachContactPointCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                owner_object_id=EntityIdVO.from_value(payload.owner_object_id),
                owner_record_id=EntityIdVO.from_value(payload.owner_record_id),
                contact_point_type=payload.contact_point_type,
                raw_value=payload.raw_value,
                is_primary=payload.is_primary,
            )
        )
    except (ContactPointOwnerNotFoundError, RuntimeObjectNotFoundError) as exc:
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
    except (
        ContactPointValidationError,
        ObjectFeatureConfigNotFoundError,
        ObjectFeatureNotEnabledError,
        RuntimeDataValidationError,
        RuntimeDataFilterError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except DomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return AttachContactPointResponseSchema(
        contact_point_id=result.contact_point_id,
        binding_id=result.binding_id,
        contact_point_created=result.contact_point_created,
        binding_created=result.binding_created,
        already_attached=result.already_attached,
    )


__all__ = ["router"]
