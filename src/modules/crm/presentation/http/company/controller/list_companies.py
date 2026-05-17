from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from src.modules.crm.application.company.query import ListCompaniesQuery
from src.modules.crm.domain.company.error import CompanyNotFoundError
from src.modules.crm.presentation.depends.application import ListCompaniesUseCaseDep
from src.modules.crm.presentation.http.company.responses import (
    CompanyResponseSchema,
    ListCompaniesResponseSchema,
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
from src.modules.shared.depends import AuthenticatedRequestContextDep
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/crm/companies", tags=["crm-companies"])


@router.get(
    "",
    response_model=ListCompaniesResponseSchema,
)
async def list_companies(
    context: AuthenticatedRequestContextDep,
    use_case: ListCompaniesUseCaseDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ListCompaniesResponseSchema:
    """HTTP endpoint списка компаний текущего tenant с limit/offset пагинацией."""

    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(
            ListCompaniesQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                limit=limit,
                offset=offset,
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

    return ListCompaniesResponseSchema(
        items=[
            CompanyResponseSchema(
                id=company.id,
                created_at=company.created_at,
                updated_at=company.updated_at,
                legal_name=company.legal_name,
            )
            for company in result
        ],
        limit=limit,
        offset=offset,
        count=len(result),
    )


__all__ = ["router"]
