from typing import Annotated
from fastapi import Depends, HTTPException

from src.modules.channels.presentation.content_delivery.assembly import (
    ContentDeliveryRuntime,
    build_content_delivery_runtime,
)
from src.modules.channels.presentation.content_media.depends import MediaTenantDep
from src.modules.channels.presentation.depends import (
    get_platforms,
    tenant_id_from_context,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.files.infrastructure.assembly import get_storage_resolver
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.crypto.depends import CipherDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep


def get_content_delivery_runtime(
    tenant: MediaTenantDep,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    uow: UoWDep,
    cipher: CipherDep,
    clock: ClockDep,
    uuid: UuidDep,
    platforms: Annotated[InstalledPlatforms, Depends(get_platforms)],
) -> ContentDeliveryRuntime:
    """Сверяет tenant HTTP и собирает порты от общего кешированного Depends UoW."""
    if tenant_id_from_context(context) != tenant.id:
        raise HTTPException(403, detail={"code": "access_denied"})
    return build_content_delivery_runtime(
        session=uow.session,
        tenant_id=tenant.id,
        base_url=tenant.base_url,
        uow=uow,
        cipher=cipher,
        clock=clock,
        uuid=uuid,
        platforms=platforms,
        storage=get_storage_resolver(),
        authorization=authorization,
    )


ContentDeliveryRuntimeDep = Annotated[
    ContentDeliveryRuntime, Depends(get_content_delivery_runtime)
]


from src.modules.channels.application.content_delivery.command.request_content_delivery.handler import (
    RequestContentDeliveryHandler,
)


def get_request_content_delivery_handler(
    runtime: ContentDeliveryRuntimeDep,
) -> RequestContentDeliveryHandler:
    """Собирает отдельный обработчик request_content_delivery."""
    return runtime.request


RequestContentDeliveryHandlerDep = Annotated[
    RequestContentDeliveryHandler, Depends(get_request_content_delivery_handler)
]


from src.modules.channels.application.content_delivery.command.request_content_reconciliation.handler import (
    RequestContentReconciliationHandler,
)


def get_request_content_reconciliation_handler(
    runtime: ContentDeliveryRuntimeDep,
) -> RequestContentReconciliationHandler:
    """Собирает отдельный обработчик request_content_reconciliation."""
    return runtime.reconcile


RequestContentReconciliationHandlerDep = Annotated[
    RequestContentReconciliationHandler,
    Depends(get_request_content_reconciliation_handler),
]


from src.modules.channels.application.content_delivery.query.get_content_deliveries.handler import (
    GetContentDeliveriesHandler,
)


def get_get_content_deliveries_handler(
    runtime: ContentDeliveryRuntimeDep,
) -> GetContentDeliveriesHandler:
    """Собирает отдельный обработчик get_content_deliveries."""
    return runtime.read


GetContentDeliveriesHandlerDep = Annotated[
    GetContentDeliveriesHandler, Depends(get_get_content_deliveries_handler)
]


from src.modules.channels.application.content_delivery.command.resolve_content_uncertainty.handler import (
    ResolveContentUncertaintyHandler,
)


def get_resolve_content_uncertainty_handler(
    runtime: ContentDeliveryRuntimeDep,
) -> ResolveContentUncertaintyHandler:
    """Собирает отдельный обработчик явного завершения неподтверждённой попытки."""
    return runtime.resolve


ResolveContentUncertaintyHandlerDep = Annotated[
    ResolveContentUncertaintyHandler, Depends(get_resolve_content_uncertainty_handler)
]
