from fastapi import HTTPException, status
from src.modules.identity.application.user.command.update_current_user_profile.command import (
    UpdateCurrentUserProfileCommand,
)
from src.modules.identity.domain.auth.error import InvalidSessionError
from src.modules.identity.domain.user.error import UserLoginUnavailableError
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.user.depends import (
    UpdateCurrentUserProfileHandlerDep,
)
from src.modules.identity.presentation.user.http.request.update_current_user_profile import (
    UpdateCurrentUserProfileRequestSchema,
)
from src.modules.identity.presentation.user.http.response.update_current_user_profile import (
    UpdateCurrentUserProfileResponseSchema,
)
from src.modules.identity.presentation.user.http.response.update_current_user_profile_email import (
    UpdateCurrentUserProfileEmailResponseSchema,
)
from src.modules.identity.domain.user.value_object.user_id import UserIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.domain_error import DomainError
from src.modules.tenancy.domain.tenant_currency_settings.error import (
    TenantCurrencySettingsNotFoundError,
)


async def update_current_user_profile(
    payload: UpdateCurrentUserProfileRequestSchema,
    context: AuthenticatedRequestContextDep,
    handler: UpdateCurrentUserProfileHandlerDep,
) -> UpdateCurrentUserProfileResponseSchema:
    """Преобразует доверенный контекст и поля сценария в отдельный HTTP-контракт."""
    principal = context.principal
    if principal is None or principal.tenant_id is None:
        raise HTTPException(status_code=403, detail="Tenant context is required.")
    try:
        result = await handler.execute(
            UpdateCurrentUserProfileCommand(
                tenant_id=EntityIdVO.from_value(principal.tenant_id),
                user_id=UserIdVO.from_value(principal.user_id),
                last_name=payload.last_name,
                first_name=payload.first_name,
                middle_name=payload.middle_name,
                interface_language=payload.interface_language,
                interface_theme=payload.interface_theme,
                timezone=payload.timezone,
                display_currency=payload.display_currency,
                display_currency_provided="display_currency"
                in payload.model_fields_set,
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
    return UpdateCurrentUserProfileResponseSchema(
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
            UpdateCurrentUserProfileEmailResponseSchema(
                id=email.id,
                email=email.email,
                is_primary=email.is_primary,
                is_verified=email.is_verified,
            )
            for email in result.emails
        ],
    )
