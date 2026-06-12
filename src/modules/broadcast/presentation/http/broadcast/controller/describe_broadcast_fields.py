from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.modules.broadcast.presentation.depends.application import (
    DescribeBroadcastFieldsUseCaseDep,
)
from src.modules.broadcast.presentation.http.broadcast.responses import (
    BroadcastFieldDescriptionResponseSchema,
    BroadcastFieldFilterCapabilityResponseSchema,
    BroadcastFieldOptionResponseSchema,
    BroadcastFieldsResponseSchema,
    BroadcastFieldSortCapabilityResponseSchema,
    BroadcastObjectDescriptionResponseSchema,
)
from src.modules.schema_registry.domain.error import (
    DataSourceNotFoundError,
    RuntimeObjectDescriptorError,
    RuntimeObjectNotFoundError,
    SchemaRegistryMetadataInconsistentError,
)
from src.modules.shared import DomainError, EntityIdVO
from src.modules.shared.presentation.identity_context import (
    AuthenticatedRequestContextDep,
)

router = APIRouter()


@router.post(
    "/broadcast/item/fields",
    response_model=BroadcastFieldsResponseSchema,
)
async def describe_broadcast_fields(
    context: AuthenticatedRequestContextDep,
    use_case: DescribeBroadcastFieldsUseCaseDep,
) -> BroadcastFieldsResponseSchema:
    """HTTP endpoint получения описания broadcast-модели текущего tenant."""

    tenant_id_raw = context.principal.tenant_id if context.principal else None
    if tenant_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        result = await use_case(EntityIdVO.from_value(tenant_id_raw))
    except (
        DataSourceNotFoundError,
        RuntimeObjectDescriptorError,
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

    return BroadcastFieldsResponseSchema(
        object=BroadcastObjectDescriptionResponseSchema(
            id=result.object_description.id,
            singular_label=result.object_description.singular_label,
            plural_label=result.object_description.plural_label,
            description=result.object_description.description,
            kind=result.object_description.kind,
        ),
        fields=[
            BroadcastFieldDescriptionResponseSchema(
                id=field.id,
                field_name=field.field_name,
                label=field.label,
                description=field.description,
                type=field.type,
                kind=field.kind,
                is_nullable=field.is_nullable,
                default_value=field.default_value,
                options=[
                    BroadcastFieldOptionResponseSchema(
                        value=option.value,
                        label=option.label,
                    )
                    for option in field.options
                ],
                filter=BroadcastFieldFilterCapabilityResponseSchema(
                    enabled=field.filter.enabled,
                    operators=list(field.filter.operators),
                    input=field.filter.input,
                    value_type=field.filter.value_type,
                    options=[
                        BroadcastFieldOptionResponseSchema(
                            value=str(option["value"]),
                            label=str(option["label"]),
                        )
                        for option in field.filter.options
                    ],
                ),
                sort=BroadcastFieldSortCapabilityResponseSchema(
                    enabled=field.sort.enabled,
                ),
            )
            for field in result.fields
        ],
    )


__all__ = ["router"]
