from dataclasses import asdict
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.error import (
    CatalogError,
    CatalogNotFoundError,
    CatalogConflictError,
)
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.domain.product.value_object.variant_id import VariantIdVO
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.product.value_object.axis import VariationAxis
from src.modules.catalog.domain.product.value_object.selection import (
    VariationSelectionVO,
)
from src.modules.catalog.application.product.structure_input import (
    VariableStructureInput,
    VariantStructureInput,
)
from src.modules.catalog.application.product.command.create_variable_product.command import (
    CreateVariableProductCommand,
)
from src.modules.catalog.presentation.product.depends import (
    CreateVariableProductHandlerDep,
)
from src.modules.catalog.presentation.product.http.request.create_variable_product import (
    CreateVariableProductRequest,
)
from src.modules.catalog.presentation.product.http.response.create_variable_product import (
    CreateVariableProductResponse,
)


async def create_variable_product(
    context: AuthenticatedRequestContextDep,
    handler: CreateVariableProductHandlerDep,
    payload: CreateVariableProductRequest,
) -> CreateVariableProductResponse:
    """Преобразует полный HTTP-контракт create_variable_product в собственную команду."""
    principal = context.principal
    if principal is None or not principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        value = payload.structure
        structure = VariableStructureInput(
            tuple(
                VariationAxis(
                    AttributeIdVO(a.attribute_id),
                    tuple(AttributeOptionIdVO(o) for o in a.option_ids),
                    a.position,
                )
                for a in value.axes
            ),
            (
                None
                if value.default_selection is None
                else VariationSelectionVO(
                    tuple(
                        (AttributeIdVO(a), AttributeOptionIdVO(o))
                        for a, o in value.default_selection.items()
                    )
                )
            ),
            tuple(
                VariantStructureInput(
                    VariationSelectionVO(
                        tuple(
                            (AttributeIdVO(a), AttributeOptionIdVO(o))
                            for a, o in v.selection.items()
                        )
                    ),
                    v.virtual,
                    None if v.variant_id is None else VariantIdVO(v.variant_id),
                )
                for v in value.variants
            ),
        )
        result = await handler.execute(
            CreateVariableProductCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                actor_id=EntityIdVO.from_value(principal.user_id),
                structure=structure,
                product_type_id=(
                    None
                    if payload.product_type_id is None
                    else ProductTypeIdVO(payload.product_type_id)
                ),
            )
        )
    except CatalogNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except CatalogConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    except CatalogError as exc:
        raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc:
        if getattr(exc.orig, "sqlstate", None) in {"23505", "23503"}:
            raise HTTPException(
                409, "Код уже существует или объект используется."
            ) from exc
        raise
    return CreateVariableProductResponse(**asdict(result))
