from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.modules.crm.application.contact.dto import (
    GetContactResultDTO,
)
from src.modules.crm.application.contact.queries import (
    GetContactQueryDTO,
)
from src.modules.crm.domain.error import ContactNotFoundError
from src.modules.crm.presentation.http.responses.contact import (
    GetContactResponseSchema,
)
from src.modules.crm.presentation.depends.use_cases import (
    GetContactUseCaseDep,
)
from src.modules.shared.depends.request_host import RequestHostDep
from src.modules.shared.domain.errors import ValidationError as DomainValidationError
from src.modules.tenancy.application.request_context_by_host.dto import (
    ResolveTenantRequestContextByHostQueryDTO,
)
from src.modules.tenancy.domain.errors import (
    TenantHostNotFoundError,
    TenantLoginUnavailableError,
)
from src.modules.tenancy.presentation.depends.use_cases import (
    TenantRequestContextByHostUseCaseDep,
)

router = APIRouter(tags=["crm-contacts"])


def _to_response(result: GetContactResultDTO) -> GetContactResponseSchema:
    payload: dict[str, object] = {
        "id": result.contact.id.value,
        "first_name": result.contact.first_name,
        "last_name": result.contact.last_name,
        "middle_name": result.contact.middle_name,
    }
    for field_name, field_value in result.custom_fields.items():
        if field_name in payload:
            continue
        payload[field_name] = field_value
    return GetContactResponseSchema.model_validate(payload)


@router.get(
    "/contacts/{contact_id}",
    response_model=GetContactResponseSchema,
)
async def get_contact(
    contact_id: UUID,
    host: RequestHostDep,
    tenant_request_context_use_case: TenantRequestContextByHostUseCaseDep,
    use_case: GetContactUseCaseDep,
) -> GetContactResponseSchema:
    try:
        tenant_context = await tenant_request_context_use_case.execute(
            ResolveTenantRequestContextByHostQueryDTO(host=host)
        )
        result = await use_case.execute(
            GetContactQueryDTO(
                tenant_id=tenant_context.tenant_id,
                contact_id=contact_id,
            )
        )
    except TenantHostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except TenantLoginUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except ContactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DomainValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return _to_response(result)


__all__ = ["router"]
