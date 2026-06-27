from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from src.modules.schema_registry.application.config.relation.command import (
    CreateRelationCommand,
    DeleteRelationCommand,
    RelationInput,
)
from src.modules.schema_registry.application.config.relation.dto import RelationDTO
from src.modules.schema_registry.application.config.relation.query import (
    ListObjectRelationsQuery,
)
from src.modules.schema_registry.domain.error import (
    FieldNotFoundError,
    ObjectNotFoundError,
    PhysicalSchemaNotFoundError,
    RelationNotFoundError,
    RuntimeObjectDescriptorError,
    SchemaRegistryError,
    SchemaRegistryMetadataInconsistentError,
    UnsupportedSchemaBackendError,
)
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.relation.value_object import (
    RuntimeRelationIdVO,
)
from src.modules.schema_registry.presentation.depends.config import (
    CreateRelationUseCaseDep,
    DeleteRelationUseCaseDep,
    ListObjectRelationsUseCaseDep,
)
from src.modules.schema_registry.presentation.http.config.relation.requests import (
    CreateRelationRequestSchema,
    DeleteRelationRequestSchema,
    ListObjectRelationsRequestSchema,
)
from src.modules.schema_registry.presentation.http.config.relation.responses import (
    ListRelationsResponseSchema,
    RelationResponseSchema,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.presentation.identity_context.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared import DomainError

router = APIRouter(prefix="/config/objects/relations", tags=["config"])


@router.post(
    "/create",
    response_model=RelationResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_relation(
    payload: CreateRelationRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: CreateRelationUseCaseDep,
) -> RelationResponseSchema:
    """HTTP endpoint создания custom relation."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    relation = payload.relation
    try:
        result = await use_case(
            CreateRelationCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                relation=RelationInput(
                    name=relation.name,
                    relation_type=relation.relation_type,
                    label=relation.label,
                    source_object_id=RuntimeObjectIdVO.from_value(
                        relation.source_object_id
                    ),
                    target_object_id=RuntimeObjectIdVO.from_value(
                        relation.target_object_id
                    ),
                    owning_object_id=(
                        RuntimeObjectIdVO.from_value(relation.owning_object_id)
                        if relation.owning_object_id is not None
                        else None
                    ),
                    fk_field_name=relation.fk_field_name,
                    referenced_object_id=(
                        RuntimeObjectIdVO.from_value(relation.referenced_object_id)
                        if relation.referenced_object_id is not None
                        else None
                    ),
                    referenced_field_name=relation.referenced_field_name,
                    source_relation_name=relation.source_relation_name,
                    target_relation_name=relation.target_relation_name,
                    relation_table_name=relation.relation_table_name,
                    source_join_column_name=relation.source_join_column_name,
                    target_join_column_name=relation.target_join_column_name,
                    on_delete=relation.on_delete,
                    is_required=relation.is_required,
                    settings=dict(relation.settings),
                ),
            )
        )
    except (ObjectNotFoundError, FieldNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (
        PhysicalSchemaNotFoundError,
        RuntimeObjectDescriptorError,
        SchemaRegistryMetadataInconsistentError,
        UnsupportedSchemaBackendError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (SchemaRegistryError, DomainError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _to_response(result)


@router.delete("/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_relation(
    payload: DeleteRelationRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: DeleteRelationUseCaseDep,
) -> Response:
    """HTTP endpoint удаления custom relation."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )

    try:
        await use_case(
            DeleteRelationCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                relation_id=RuntimeRelationIdVO.from_value(payload.relation_id),
            )
        )
    except RelationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (
        PhysicalSchemaNotFoundError,
        RuntimeObjectDescriptorError,
        SchemaRegistryMetadataInconsistentError,
        UnsupportedSchemaBackendError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (SchemaRegistryError, DomainError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/list", response_model=ListRelationsResponseSchema)
async def list_relations(
    payload: ListObjectRelationsRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: ListObjectRelationsUseCaseDep,
) -> ListRelationsResponseSchema:
    """HTTP endpoint списка object relations."""
    return await _list_relations(payload=payload, context=context, use_case=use_case)


@router.post("/schema", response_model=ListRelationsResponseSchema)
async def relation_schema(
    payload: ListObjectRelationsRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: ListObjectRelationsUseCaseDep,
) -> ListRelationsResponseSchema:
    """HTTP endpoint schema-представления object relations."""
    return await _list_relations(payload=payload, context=context, use_case=use_case)


async def _list_relations(
    *,
    payload: ListObjectRelationsRequestSchema,
    context: AuthenticatedRequestContextDep,
    use_case: ListObjectRelationsUseCaseDep,
) -> ListRelationsResponseSchema:
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
    try:
        result = await use_case(
            ListObjectRelationsQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                object_id=RuntimeObjectIdVO.from_value(payload.object_id),
            )
        )
    except ObjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (
        PhysicalSchemaNotFoundError,
        RuntimeObjectDescriptorError,
        SchemaRegistryMetadataInconsistentError,
        UnsupportedSchemaBackendError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (SchemaRegistryError, DomainError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    items = [_to_response(item) for item in result]
    return ListRelationsResponseSchema(items=items, count=len(items))


def _to_response(dto: RelationDTO) -> RelationResponseSchema:
    return RelationResponseSchema(
        id=dto.id,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
        name=dto.name,
        label=dto.label,
        relation_type=dto.relation_type,
        source_object_id=dto.source_object_id,
        target_object_id=dto.target_object_id,
        source_object=dto.source_object,
        target_object=dto.target_object,
        source_relation_name=dto.source_relation_name,
        target_relation_name=dto.target_relation_name,
        owning_object_id=dto.owning_object_id,
        owning_object=dto.owning_object,
        fk_field_id=dto.fk_field_id,
        fk_field=dto.fk_field,
        referenced_object_id=dto.referenced_object_id,
        referenced_object=dto.referenced_object,
        referenced_field_id=dto.referenced_field_id,
        referenced_field=dto.referenced_field,
        relation_table_name=dto.relation_table_name,
        source_join_column_name=dto.source_join_column_name,
        target_join_column_name=dto.target_join_column_name,
        on_delete=dto.on_delete,
        is_required=dto.is_required,
        is_unique=dto.is_unique,
        kind=dto.kind,
        settings=dto.settings,
    )


__all__ = ["router"]
