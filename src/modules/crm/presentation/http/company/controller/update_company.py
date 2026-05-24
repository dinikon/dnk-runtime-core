from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.modules.crm.application.company.command import UpdateCompanyCommand
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.crm.presentation.depends.application import UpdateCompanyUseCaseDep
from src.modules.crm.presentation.http.company.requests import (
    UpdateCompanyRequestSchema,
)
from src.modules.crm.presentation.http.company.responses import CompanyResponseSchema
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
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/crm/companies", tags=["crm-companies"])


@router.put(
    "/{company_id}",
    response_model=CompanyResponseSchema,
)
async def update_company(
    company_id: UUID,
    payload: UpdateCompanyRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: UpdateCompanyUseCaseDep,
) -> CompanyResponseSchema:
    """HTTP endpoint обновления компании текущего tenant."""

    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    command = UpdateCompanyCommand(
        tenant_id=EntityIdVO.from_value(principal.tenant_id),
        company_id=CompanyIdVO.from_value(company_id),
        legal_name=payload.legal_name,
    )

    try:
        result = await use_case(command)
    except CompanyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (
        RuntimeDataPersistenceError,
        RuntimeDataPolicyError,
        RuntimeObjectDescriptorError,
        RuntimeObjectNotFoundError,
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

    return CompanyResponseSchema(
        id=result.id,
        created_at=result.created_at,
        updated_at=result.updated_at,
        legal_name=result.legal_name,
    )


__all__ = ["router"]
