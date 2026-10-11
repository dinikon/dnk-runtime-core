from src.modules.identity.application.user.command.update_current_user_profile.command import (
    UpdateCurrentUserProfileCommand,
)
from src.modules.identity.application.user.command.update_current_user_profile.dto import (
    UpdateCurrentUserProfileResultDTO,
)
from src.modules.identity.application.user.command.update_current_user_profile.email_dto import (
    UpdateCurrentUserProfileEmailDTO,
)
from src.modules.identity.application.user.port.currency_validator import (
    ProfileCurrencyValidatorProtocol,
)
from src.modules.identity.application.user.port.tenant_currency_settings import (
    ProfileTenantCurrencySettingsProtocol,
)
from src.modules.identity.domain.auth.error import InvalidSessionError
from src.modules.identity.domain.user.error import UserLoginUnavailableError
from src.modules.identity.domain.user.repository import UserRepositoryProtocol
from src.modules.shared.domain.value_object.currency import CurrencyVO


class UpdateCurrentUserProfileHandler:
    """Изменяет профиль собственного пользователя в уже открытом tenant UoW."""

    def __init__(
        self,
        users_repository: UserRepositoryProtocol,
        currency_validator: ProfileCurrencyValidatorProtocol,
        settings: ProfileTenantCurrencySettingsProtocol,
    ) -> None:
        """Принимает порты агрегата, проверки валюты и настроек Tenant без UoW."""
        self._users = users_repository
        self._currency_validator = currency_validator
        self._settings = settings

    async def execute(
        self, command: UpdateCurrentUserProfileCommand
    ) -> UpdateCurrentUserProfileResultDTO:
        """Проверяет выбор, меняет агрегат и сохраняет профиль; commit выполняется снаружи."""
        currency = None
        if command.display_currency_provided and command.display_currency is not None:
            currency = CurrencyVO.from_value(command.display_currency)
            await self._currency_validator.ensure_supported(currency)
        base = await self._settings.get_base_currency(command.tenant_id)
        user = await self._users.get_by_id(
            command.user_id, tenant_id=command.tenant_id, for_update=True
        )
        if user is None or user.tenant_id != command.tenant_id:
            raise InvalidSessionError()
        if not user.can_login():
            raise UserLoginUnavailableError()
        user.update_profile(
            last_name=command.last_name,
            first_name=command.first_name,
            middle_name=command.middle_name,
            interface_language=command.interface_language,
            interface_theme=command.interface_theme,
            timezone=command.timezone,
            display_currency=currency,
            display_currency_provided=command.display_currency_provided,
        )
        await self._users.update_profile(user, tenant_id=command.tenant_id)
        selected = (
            None if user.display_currency is None else user.display_currency.value
        )
        return UpdateCurrentUserProfileResultDTO(
            id=user.id.uuid,
            status=user.status,
            role=user.role,
            last_name=user.last_name,
            first_name=user.first_name,
            middle_name=user.middle_name,
            avatar=user.avatar,
            interface_language=user.interface_language,
            interface_theme=user.interface_theme,
            timezone=user.timezone,
            display_currency=selected,
            effective_display_currency=selected or base.value,
            emails=[
                UpdateCurrentUserProfileEmailDTO(
                    id=email.id.uuid,
                    email=email.email,
                    is_primary=email.is_primary,
                    is_verified=email.is_verified,
                )
                for email in user.emails
                if not email.is_deleted
            ],
        )
