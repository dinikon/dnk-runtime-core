from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from src.modules.crm.application.company.command import DeleteCompanyCommand
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.crm.presentation.depends.application import DeleteCompanyUseCaseDep
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
from src.modules.shared import EntityIdVO
from src.modules.shared.depends import AuthenticatedRequestContextDep
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/crm/companies", tags=["crm-companies"])


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_company(
    company_id: UUID,
    context: AuthenticatedRequestContextDep,
    use_case: DeleteCompanyUseCaseDep,
) -> Response:
    """HTTP endpoint удаления компании текущего tenant."""

    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        await use_case(
            DeleteCompanyCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                company_id=CompanyIdVO.from_value(company_id),
            )
        )
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

    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
