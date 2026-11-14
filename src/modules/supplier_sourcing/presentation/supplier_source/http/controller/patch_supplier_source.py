from uuid import UUID
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.supplier_sourcing.domain.error import SupplierSourcingError
from src.modules.supplier_sourcing.domain.supplier_source.error import (
    SupplierSourceNotFoundError,
    SupplierNotFoundError,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.identifier import (
    SupplierSourceIdVO,
)
from src.modules.supplier_sourcing.presentation.supplier_source.depends import (
    UpdateSupplierSourceHandlerDep,
)
from src.modules.supplier_sourcing.presentation.supplier_source.http.request.patch_supplier_source import (
    PatchSupplierSourceRequest,
)
from src.modules.supplier_sourcing.presentation.supplier_source.http.response.patch_supplier_source import (
    PatchSupplierSourceResponse,
)
from src.modules.supplier_sourcing.application.supplier_source.command.update_supplier_source.command import (
    UpdateSupplierSourceCommand,
)
from src.modules.supplier_sourcing.application.supplier_source.stock_update_policy import (
    SupplierStockUpdatePolicyInput,
)


async def patch_supplier_source(
    source_id: UUID,
    payload: PatchSupplierSourceRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateSupplierSourceHandlerDep,
) -> PatchSupplierSourceResponse:
    """Преобразует PATCH в команду и переводит ожидаемые отказы."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            UpdateSupplierSourceCommand(
                source_id=SupplierSourceIdVO.from_value(source_id),
                fields=frozenset(payload.model_fields_set),
                name=payload.name,
                external_warehouse_code=payload.external_warehouse_code,
                fulfillment_modes=(
                    frozenset(payload.fulfillment_modes)
                    if payload.fulfillment_modes is not None
                    else None
                ),
                default_lead_time_seconds=payload.default_lead_time_seconds,
                stock_update_policy=(
                    SupplierStockUpdatePolicyInput(
                        payload.stock_update_policy.ttl_seconds,
                        payload.stock_update_policy.stale_behavior,
                        payload.stock_update_policy.missing_sku_behavior,
                    )
                    if payload.stock_update_policy is not None
                    else None
                ),
                is_active=payload.is_active,
            )
        )
    except (SupplierSourceNotFoundError, SupplierNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except SupplierSourcingError as exc:
        raise HTTPException(422, str(exc)) from exc
    return PatchSupplierSourceResponse.from_dto(result)
