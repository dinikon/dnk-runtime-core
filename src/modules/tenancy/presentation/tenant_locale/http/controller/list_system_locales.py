from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.tenancy.application.tenant_locale.query.list_system_locales.query import (
    ListSystemLocalesQuery,
)
from src.modules.tenancy.presentation.tenant_locale.depends import (
    ListSystemLocalesHandlerDep,
)
from src.modules.tenancy.presentation.tenant_locale.http.response.system_locale import (
    SystemLocaleResponse,
)


async def list_system_locales(
    context: AuthenticatedRequestContextDep,
    handler: ListSystemLocalesHandlerDep,
) -> list[SystemLocaleResponse]:
    """Показывает разрешённые системой локали."""
    result = await handler.execute(ListSystemLocalesQuery())
    return [SystemLocaleResponse.from_dto(item) for item in result]
