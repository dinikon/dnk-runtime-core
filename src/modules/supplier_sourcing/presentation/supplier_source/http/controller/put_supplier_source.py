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
from src.modules.supplier_sourcing.presentation.supplier_source.http.request.put_supplier_source import (
    PutSupplierSourceRequest,
)
from src.modules.supplier_sourcing.presentation.supplier_source.http.response.put_supplier_source import (
    PutSupplierSourceResponse,
)
from src.modules.supplier_sourcing.application.supplier_source.command.update_supplier_source.command import (
    UpdateSupplierSourceCommand,
)
from src.modules.supplier_sourcing.application.supplier_source.stock_update_policy import (
    SupplierStockUpdatePolicyInput,
)


async def put_supplier_source(
    source_id: UUID,
    payload: PutSupplierSourceRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateSupplierSourceHandlerDep,
) -> PutSupplierSourceResponse:
    """Преобразует PUT в команду и переводит ожидаемые отказы."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            UpdateSupplierSourceCommand(
                source_id=SupplierSourceIdVO.from_value(source_id),
                fields=frozenset(payload.model_fields_set),
                name=payload.name,
                external_warehouse_code=payload.external_warehouse_code,
                fulfillment_modes=frozenset(payload.fulfillment_modes),
                default_lead_time_seconds=payload.default_lead_time_seconds,
                stock_update_policy=SupplierStockUpdatePolicyInput(
                    payload.stock_update_policy.ttl_seconds,
                    payload.stock_update_policy.stale_behavior,
                    payload.stock_update_policy.missing_sku_behavior,
                ),
                is_active=payload.is_active,
            )
        )
    except (SupplierSourceNotFoundError, SupplierNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except SupplierSourcingError as exc:
        raise HTTPException(422, str(exc)) from exc
    return PutSupplierSourceResponse.from_dto(result)
