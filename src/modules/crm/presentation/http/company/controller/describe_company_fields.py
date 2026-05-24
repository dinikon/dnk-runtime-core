from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.crm.presentation.depends.application import (
    DescribeCompanyFieldsUseCaseDep,
)
from src.modules.crm.presentation.http.company.responses import (
    CompanyFieldDescriptionResponseSchema,
    CompanyFieldOptionResponseSchema,
    CompanyFieldsResponseSchema,
    CompanyObjectDescriptionResponseSchema,
)
from src.modules.schema_registry.domain.error import (
    DataSourceNotFoundError,
    RuntimeObjectNotFoundError,
    SchemaRegistryMetadataInconsistentError,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.presentation import AuthenticatedRequestContextDep
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/crm/companies", tags=["crm-companies"])


@router.post(
    "/fields",
    response_model=CompanyFieldsResponseSchema,
)
async def describe_company_fields(
    context: AuthenticatedRequestContextDep,
    use_case: DescribeCompanyFieldsUseCaseDep,
) -> CompanyFieldsResponseSchema:
    """HTTP endpoint получения описания CRM-модели company для tenant."""

    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(EntityIdVO.from_value(principal.tenant_id))
    except (
        DataSourceNotFoundError,
        RuntimeObjectNotFoundError,
        SchemaRegistryMetadataInconsistentError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except DomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return CompanyFieldsResponseSchema(
        object=CompanyObjectDescriptionResponseSchema(
            id=result.object_description.id,
            singular_label=result.object_description.singular_label,
            plural_label=result.object_description.plural_label,
            description=result.object_description.description,
            kind=result.object_description.kind,
        ),
        fields=[
            CompanyFieldDescriptionResponseSchema(
                id=field.id,
                field_name=field.field_name,
                label=field.label,
                description=field.description,
                type=field.type,
                kind=field.kind,
                is_nullable=field.is_nullable,
                default_value=field.default_value,
                options=[
                    CompanyFieldOptionResponseSchema(
                        value=option.value,
                        label=option.label,
                    )
                    for option in field.options
                ],
            )
            for field in result.fields
        ],
    )


__all__ = ["router"]
