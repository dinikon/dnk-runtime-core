from __future__ import annotations

from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.modules.custom_object.application.commands import (
    CreateCustomObjectCommandDTO,
    CreateCustomObjectFieldCommandDTO,
)
from src.modules.custom_object.application.dto import (
    GetCustomObjectRecordResultDTO,
)
from src.modules.custom_object.application.queries import (
    GetCustomObjectRecordQueryDTO,
)
from src.modules.custom_object.domain import (
    CustomObjectNotFoundError,
    CustomObjectRecordNotFoundError,
)
from src.modules.custom_object.presentation.depends.use_cases import (
    CreateCustomObjectFieldUseCaseDep,
    CreateCustomObjectUseCaseDep,
    GetCustomObjectRecordUseCaseDep,
)
from src.modules.custom_object.presentation.http.requests import (
    CreateCustomObjectFieldRequestSchema,
    CreateCustomObjectRequestSchema,
)
from src.modules.custom_object.presentation.http.responses import (
    CreateCustomObjectFieldResponseSchema,
    CreateCustomObjectResponseSchema,
    GetCustomObjectRecordResponseSchema,
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

router = APIRouter(tags=["custom-objects"])


def _to_record_response(
    result: GetCustomObjectRecordResultDTO,
) -> GetCustomObjectRecordResponseSchema:
    payload: dict[str, object] = {"id": result.record_id}
    for field_name, field_value in result.values.items():
        if field_name in payload:
            continue
        payload[field_name] = field_value
    return GetCustomObjectRecordResponseSchema.model_validate(payload)


@router.post(
    "/custom-objects",
    response_model=CreateCustomObjectResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_custom_object(
    payload: CreateCustomObjectRequestSchema,
    host: RequestHostDep,
    tenant_request_context_use_case: TenantRequestContextByHostUseCaseDep,
    use_case: CreateCustomObjectUseCaseDep,
) -> CreateCustomObjectResponseSchema:
    try:
        tenant_context = await tenant_request_context_use_case.execute(
            ResolveTenantRequestContextByHostQueryDTO(host=host)
        )
        result = await use_case.execute(
            CreateCustomObjectCommandDTO(
                tenant_id=tenant_context.tenant_id,
                object_name_singular=payload.object_name_singular,
                object_name_plural=payload.object_name_plural,
                object_label_singular=payload.object_label_singular,
                object_label_plural=payload.object_label_plural,
                description=payload.description,
                icon=payload.icon,
                shortcut=payload.shortcut,
                is_active=payload.is_active,
                is_ui_read_only=payload.is_ui_read_only,
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
    except DomainValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return CreateCustomObjectResponseSchema.model_validate(asdict(result))


@router.post(
    "/custom-objects/{object_name_singular}/fields",
    response_model=CreateCustomObjectFieldResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_custom_object_field(
    object_name_singular: str,
    payload: CreateCustomObjectFieldRequestSchema,
    host: RequestHostDep,
    tenant_request_context_use_case: TenantRequestContextByHostUseCaseDep,
    use_case: CreateCustomObjectFieldUseCaseDep,
) -> CreateCustomObjectFieldResponseSchema:
    try:
        tenant_context = await tenant_request_context_use_case.execute(
            ResolveTenantRequestContextByHostQueryDTO(host=host)
        )
        result = await use_case.execute(
            CreateCustomObjectFieldCommandDTO(
                tenant_id=tenant_context.tenant_id,
                object_name_singular=object_name_singular,
                field_type=payload.field_type,
                field_name=payload.field_name,
                label=payload.label,
                description=payload.description,
                icon=payload.icon,
                is_active=payload.is_active,
                is_unique=payload.is_unique,
                is_index=payload.is_index,
                is_nullable=payload.is_nullable,
                is_ui_read_only=payload.is_ui_read_only,
                is_searchable=payload.is_searchable,
                options=payload.options,
                settings=payload.settings,
                default_value=payload.default_value,
                relation_target_object_name=payload.relation_target_object_name,
                relation_target_field_id=payload.relation_target_field_id,
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
    except CustomObjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DomainValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return CreateCustomObjectFieldResponseSchema.model_validate(asdict(result))


@router.get(
    "/custom-objects/{object_name_singular}/records/{record_id}",
    response_model=GetCustomObjectRecordResponseSchema,
)
async def get_custom_object_record(
    object_name_singular: str,
    record_id: UUID,
    host: RequestHostDep,
    tenant_request_context_use_case: TenantRequestContextByHostUseCaseDep,
    use_case: GetCustomObjectRecordUseCaseDep,
) -> GetCustomObjectRecordResponseSchema:
    try:
        tenant_context = await tenant_request_context_use_case.execute(
            ResolveTenantRequestContextByHostQueryDTO(host=host)
        )
        result = await use_case.execute(
            GetCustomObjectRecordQueryDTO(
                tenant_id=tenant_context.tenant_id,
                object_name_singular=object_name_singular,
                record_id=record_id,
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
    except (CustomObjectNotFoundError, CustomObjectRecordNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DomainValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return _to_record_response(result)


__all__ = ["router"]
