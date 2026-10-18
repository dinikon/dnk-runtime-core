from fastapi import HTTPException, status
from src.modules.identity.application.user.query.get_current_user.query import (
    GetCurrentUserQuery,
)
from src.modules.identity.domain.auth.error import InvalidSessionError
from src.modules.identity.domain.user.error import UserLoginUnavailableError
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.user.depends import GetCurrentUserHandlerDep
from src.modules.identity.presentation.user.http.response.get_current_user import (
    GetCurrentUserResponseSchema,
)
from src.modules.identity.presentation.user.http.response.get_current_user_email import (
    GetCurrentUserEmailResponseSchema,
)
from src.modules.identity.domain.user.value_object.user_id import UserIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.domain_error import DomainError
from src.modules.tenancy.domain.tenant_currency_settings.error import (
    TenantCurrencySettingsNotFoundError,
)


async def get_current_user(
    context: AuthenticatedRequestContextDep,
    handler: GetCurrentUserHandlerDep,
) -> GetCurrentUserResponseSchema:
    """Преобразует доверенный контекст и поля сценария в отдельный HTTP-контракт."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(status_code=403, detail="Tenant context is required.")
    try:
        result = await handler.execute(
            GetCurrentUserQuery(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                user_id=UserIdVO.from_value(principal.user_id),
            )
        )
    except InvalidSessionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except UserLoginUnavailableError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except TenantCurrencySettingsNotFoundError as exc:
        raise HTTPException(
            status_code=503, detail="Tenant currency settings unavailable."
        ) from exc
    except DomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    return GetCurrentUserResponseSchema(
        id=result.id,
        status=result.status,
        role=result.role,
        last_name=result.last_name,
        first_name=result.first_name,
        middle_name=result.middle_name,
        avatar=result.avatar,
        interface_language=result.interface_language,
        interface_theme=result.interface_theme,
        timezone=result.timezone,
        display_currency=result.display_currency,
        effective_display_currency=result.effective_display_currency,
        emails=[
            GetCurrentUserEmailResponseSchema(
                id=email.id,
                email=email.email,
                is_primary=email.is_primary,
                is_verified=email.is_verified,
            )
            for email in result.emails
        ],
    )
