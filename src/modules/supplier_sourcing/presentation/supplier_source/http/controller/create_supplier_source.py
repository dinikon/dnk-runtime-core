from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierReferenceVO,
)
from fastapi import HTTPException
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.supplier_sourcing.domain.error import SupplierSourcingError
from src.modules.supplier_sourcing.domain.supplier_source.error import (
    SupplierSourceNotFoundError,
    SupplierNotFoundError,
)
from src.modules.supplier_sourcing.presentation.supplier_source.depends import (
    CreateSupplierSourceHandlerDep,
)
from src.modules.supplier_sourcing.presentation.supplier_source.http.request.create_supplier_source import (
    CreateSupplierSourceRequest,
)
from src.modules.supplier_sourcing.presentation.supplier_source.http.response.create_supplier_source import (
    CreateSupplierSourceResponse,
)
from src.modules.supplier_sourcing.application.supplier_source.command.create_supplier_source.command import (
    CreateSupplierSourceCommand,
)
from src.modules.supplier_sourcing.application.supplier_source.stock_update_policy import (
    SupplierStockUpdatePolicyInput,
)


async def create_supplier_source(
    payload: CreateSupplierSourceRequest,
    context: AuthenticatedRequestContextDep,
    handler: CreateSupplierSourceHandlerDep,
) -> CreateSupplierSourceResponse:
    """Преобразует CREATE в команду и переводит ожидаемые отказы."""
    if context.principal is None or not context.principal.tenant_id:
        raise HTTPException(403, "Tenant context is required.")
    try:
        result = await handler.execute(
            CreateSupplierSourceCommand(
                supplier=SupplierReferenceVO.from_value(
                    payload.supplier_model_key.value, payload.supplier_id
                ),
                name=payload.name,
                external_warehouse_code=payload.external_warehouse_code,
                fulfillment_modes=frozenset(payload.fulfillment_modes),
                default_lead_time_seconds=payload.default_lead_time_seconds,
                stock_update_policy=SupplierStockUpdatePolicyInput(
                    payload.stock_update_policy.ttl_seconds,
                    payload.stock_update_policy.stale_behavior,
                    payload.stock_update_policy.missing_sku_behavior,
                ),
            )
        )
    except (SupplierSourceNotFoundError, SupplierNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except SupplierSourcingError as exc:
        raise HTTPException(422, str(exc)) from exc
    return CreateSupplierSourceResponse.from_dto(result)
