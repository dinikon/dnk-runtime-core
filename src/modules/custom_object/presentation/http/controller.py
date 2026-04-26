from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from src.modules.custom_object.application import (
    AddCustomFieldCommand,
    CreateCustomObjectCommand,
    CreateCustomRecordCommand,
    CustomFieldInput,
    CustomObjectByIdCommand,
    CustomRecordByIdCommand,
    DeleteCustomFieldCommand,
    ListCustomRecordsQuery,
    UpdateCustomRecordCommand,
    parse_filter_payload,
    parse_sort_payload,
)
from src.modules.custom_object.application.dto import (
    CustomFieldDTO,
    CustomObjectDTO,
    CustomRecordDTO,
)
from src.modules.custom_object.domain import (
    CustomObjectFieldNotFoundError,
    CustomObjectNotFoundError,
    CustomObjectRecordNotFoundError,
    CustomObjectValidationError,
)
from src.modules.custom_object.presentation.depends.application import (
    AddCustomFieldUseCaseDep,
    CreateCustomObjectUseCaseDep,
    CreateCustomRecordUseCaseDep,
    DeleteCustomFieldUseCaseDep,
    DeleteCustomObjectUseCaseDep,
    DeleteCustomRecordUseCaseDep,
    DescribeCustomObjectUseCaseDep,
    GetCustomRecordUseCaseDep,
    ListCustomObjectsUseCaseDep,
    ListCustomRecordsUseCaseDep,
    UpdateCustomRecordUseCaseDep,
)
from src.modules.custom_object.presentation.http.requests import (
    CreateCustomFieldRequestSchema,
    CreateCustomObjectRequestSchema,
    CreateCustomRecordRequestSchema,
    CustomFieldRequestSchema,
    CustomRecordByIdRequestSchema,
    DeleteCustomFieldRequestSchema,
    ListCustomRecordsRequestSchema,
    ObjectIdRequestSchema,
    UpdateCustomRecordRequestSchema,
)
from src.modules.custom_object.presentation.http.responses import (
    CustomFieldResponseSchema,
    CustomObjectResponseSchema,
    CustomRecordResponseSchema,
    ListCustomObjectsResponseSchema,
    ListCustomRecordsResponseSchema,
)
from src.modules.runtime_data import (
    RuntimeDataFilterError,
    RuntimeDataPersistenceError,
    RuntimeDataPolicyError,
    RuntimeDataValidationError,
)
from src.modules.schema_registry.domain.error import (
    PhysicalSchemaNotFoundError,
    RuntimeObjectDescriptorError,
    SchemaRegistryMetadataInconsistentError,
    SchemaRegistryError,
    UnsupportedSchemaBackendError,
)
from src.modules.schema_registry.domain.field.value_object import RuntimeFieldIdVO
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.shared import TenantIdVO
from src.modules.shared.depends import AuthenticatedRequestContextDep
from src.modules.shared.domain.errors import DomainError

router = APIRouter(prefix="/custom-objects", tags=["custom-objects"])


@router.post("/list", response_model=ListCustomObjectsResponseSchema)
async def list_custom_objects(
    context: AuthenticatedRequestContextDep,
    use_case: ListCustomObjectsUseCaseDep,
) -> ListCustomObjectsResponseSchema:
    """HTTP endpoint списка custom objects."""
    try:
        result = await use_case(tenant_id=_tenant_id(context))
    except Exception as exc:
        _raise_http(exc)
    return ListCustomObjectsResponseSchema(
        items=[_object_response(item) for item in result],
        count=len(result),
    )


@router.post(
    "/create",
    response_model=CustomObjectResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_custom_object(
    payload: CreateCustomObjectRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: CreateCustomObjectUseCaseDep,
) -> CustomObjectResponseSchema:
    """HTTP endpoint создания custom object."""
    command = CreateCustomObjectCommand(
        tenant_id=_tenant_id(context),
        singular_name=payload.singular_name,
        plural_name=payload.plural_name,
        singular_label=payload.singular_label,
        plural_label=payload.plural_label,
        description=payload.description,
        fields=tuple(_field_input(field) for field in payload.fields),
    )
    try:
        result = await use_case(command)
    except Exception as exc:
        _raise_http(exc)
    return _object_response(result)


@router.delete("/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_object(
    payload: ObjectIdRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: DeleteCustomObjectUseCaseDep,
) -> Response:
    """HTTP endpoint hard delete custom object."""
    try:
        await use_case(
            CustomObjectByIdCommand(
                tenant_id=_tenant_id(context),
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
            )
        )
    except Exception as exc:
        _raise_http(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/schema", response_model=CustomObjectResponseSchema)
async def describe_custom_object(
    payload: ObjectIdRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: DescribeCustomObjectUseCaseDep,
) -> CustomObjectResponseSchema:
    """HTTP endpoint схемы custom object."""
    try:
        result = await use_case(
            CustomObjectByIdCommand(
                tenant_id=_tenant_id(context),
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
            )
        )
    except Exception as exc:
        _raise_http(exc)
    return _object_response(result)


@router.post("/fields/create", response_model=CustomObjectResponseSchema)
async def create_custom_field(
    payload: CreateCustomFieldRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: AddCustomFieldUseCaseDep,
) -> CustomObjectResponseSchema:
    """HTTP endpoint добавления custom field."""
    try:
        result = await use_case(
            AddCustomFieldCommand(
                tenant_id=_tenant_id(context),
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
                field=_field_input(payload.field),
            )
        )
    except Exception as exc:
        _raise_http(exc)
    return _object_response(result)


@router.delete("/fields/delete", response_model=CustomObjectResponseSchema)
async def delete_custom_field(
    payload: DeleteCustomFieldRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: DeleteCustomFieldUseCaseDep,
) -> CustomObjectResponseSchema:
    """HTTP endpoint удаления custom field."""
    try:
        result = await use_case(
            DeleteCustomFieldCommand(
                tenant_id=_tenant_id(context),
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
                field_id=RuntimeFieldIdVO.from_value(payload.field_id),
            )
        )
    except Exception as exc:
        _raise_http(exc)
    return _object_response(result)


@router.post(
    "/records/create",
    response_model=CustomRecordResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_custom_record(
    payload: CreateCustomRecordRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: CreateCustomRecordUseCaseDep,
) -> CustomRecordResponseSchema:
    """HTTP endpoint создания custom-object record."""
    try:
        result = await use_case(
            CreateCustomRecordCommand(
                tenant_id=_tenant_id(context),
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
                values=payload.values,
            )
        )
    except Exception as exc:
        _raise_http(exc)
    return _record_response(result)


@router.post("/records/detail", response_model=CustomRecordResponseSchema)
async def get_custom_record(
    payload: CustomRecordByIdRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: GetCustomRecordUseCaseDep,
) -> CustomRecordResponseSchema:
    """HTTP endpoint чтения custom-object record."""
    try:
        result = await use_case(
            CustomRecordByIdCommand(
                tenant_id=_tenant_id(context),
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
                row_id=payload.row_id,
            )
        )
    except Exception as exc:
        _raise_http(exc)
    return _record_response(result)


@router.post("/records/list", response_model=ListCustomRecordsResponseSchema)
async def list_custom_records(
    payload: ListCustomRecordsRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: ListCustomRecordsUseCaseDep,
) -> ListCustomRecordsResponseSchema:
    """HTTP endpoint списка custom-object records."""
    try:
        result = await use_case(
            ListCustomRecordsQuery(
                tenant_id=_tenant_id(context),
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
                filters=parse_filter_payload(payload.filter),
                sorting=parse_sort_payload(payload.sort),
                limit=payload.limit,
                offset=payload.offset,
            )
        )
    except Exception as exc:
        _raise_http(exc)
    return ListCustomRecordsResponseSchema(
        items=[_record_response(item) for item in result],
        limit=payload.limit,
        offset=payload.offset,
        count=len(result),
    )


@router.patch("/records/update", response_model=CustomRecordResponseSchema)
@router.put("/records/update", response_model=CustomRecordResponseSchema)
async def update_custom_record(
    payload: UpdateCustomRecordRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: UpdateCustomRecordUseCaseDep,
) -> CustomRecordResponseSchema:
    """HTTP endpoint обновления custom-object record."""
    try:
        result = await use_case(
            UpdateCustomRecordCommand(
                tenant_id=_tenant_id(context),
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
                row_id=payload.row_id,
                values=payload.values,
            )
        )
    except Exception as exc:
        _raise_http(exc)
    return _record_response(result)


@router.delete("/records/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_record(
    payload: CustomRecordByIdRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: DeleteCustomRecordUseCaseDep,
) -> Response:
    """HTTP endpoint удаления custom-object record."""
    try:
        await use_case(
            CustomRecordByIdCommand(
                tenant_id=_tenant_id(context),
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
                row_id=payload.row_id,
            )
        )
    except Exception as exc:
        _raise_http(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _tenant_id(context) -> TenantIdVO:
    raw_value = context.principal.tenant_id if context.principal else None
    if raw_value is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
    return TenantIdVO.from_value(raw_value)


def _field_input(payload: CustomFieldRequestSchema) -> CustomFieldInput:
    return CustomFieldInput(
        field_name=payload.field_name,
        type=payload.type,
        label=payload.label,
        description=payload.description,
        is_nullable=payload.is_nullable,
        default_value=payload.default_value,
        options=dict(payload.options),
        settings=dict(payload.settings),
    )


def _object_response(dto: CustomObjectDTO) -> CustomObjectResponseSchema:
    return CustomObjectResponseSchema(
        id=dto.id,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
        singular_name=dto.singular_name,
        plural_name=dto.plural_name,
        singular_label=dto.singular_label,
        plural_label=dto.plural_label,
        description=dto.description,
        kind=dto.kind,
        fields=[_field_response(field) for field in dto.fields],
    )


def _field_response(dto: CustomFieldDTO) -> CustomFieldResponseSchema:
    return CustomFieldResponseSchema(
        id=dto.id,
        field_name=dto.field_name,
        label=dto.label,
        description=dto.description,
        type=dto.type,
        is_nullable=dto.is_nullable,
        default_value=dto.default_value,
        options=dto.options,
        kind=dto.kind,
    )


def _record_response(dto: CustomRecordDTO) -> CustomRecordResponseSchema:
    return CustomRecordResponseSchema(
        object_id=dto.object_id,
        row_id=dto.row_id,
        values=dict(dto.values),
    )


def _raise_http(exc: Exception):
    if isinstance(
        exc,
        (
            CustomObjectNotFoundError,
            CustomObjectFieldNotFoundError,
            CustomObjectRecordNotFoundError,
        ),
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    if isinstance(
        exc,
        (
            RuntimeDataPersistenceError,
            RuntimeDataPolicyError,
            RuntimeObjectDescriptorError,
            PhysicalSchemaNotFoundError,
            SchemaRegistryMetadataInconsistentError,
            UnsupportedSchemaBackendError,
        ),
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    if isinstance(
        exc,
        (
            CustomObjectValidationError,
            RuntimeDataValidationError,
            RuntimeDataFilterError,
            SchemaRegistryError,
            DomainError,
        ),
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    raise exc


__all__ = ["router"]
