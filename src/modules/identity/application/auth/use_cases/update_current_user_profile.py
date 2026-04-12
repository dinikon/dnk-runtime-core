from __future__ import annotations

from src.modules.identity.application.auth.dto import (
    GetCurrentUserEmailDTO,
    UpdateCurrentUserProfileCommandDTO,
    UpdateCurrentUserProfileResultDTO,
)
from src.modules.identity.application.auth.ports.repositories import (
    AuthUserRepositoryPort,
)
from src.modules.identity.application.auth.ports.tenant_context import (
    TenantContextReaderPort,
)
from src.modules.identity.application.auth.ports.token_store import (
    SessionStorePort,
)
from src.modules.identity.domain.errors import (
    InvalidSessionError,
    UserLoginUnavailableError,
)
from src.modules.shared.http.host import normalize_host
from src.modules.shared.db.uow import UnitOfWorkProtocol


class UpdateCurrentUserProfileUseCase:
    """Use case обновления профиля текущего пользователя по session."""

    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        tenant_context_reader: TenantContextReaderPort,
        users_repository: AuthUserRepositoryPort,
        session_store: SessionStorePort,
    ):
        """Инициализирует use case UoW, tenant context reader, user repo и session store."""
        self._uow = uow
        self._tenant_context_reader = tenant_context_reader
        self._users_repository = users_repository
        self._session_store = session_store

    async def execute(
        self,
        dto: UpdateCurrentUserProfileCommandDTO,
    ) -> UpdateCurrentUserProfileResultDTO:
        """Проверяет session, обновляет профиль и коммитит изменения через UoW."""
        host = normalize_host(dto.host)
        tenant_context = await self._tenant_context_reader.get_by_host(host)

        if not dto.session_token:
            raise InvalidSessionError()

        session = await self._session_store.get_session(
            tenant_context.tenant_id,
            dto.session_token,
        )
        if session is None:
            raise InvalidSessionError()
        if (
            session.tenant_id != tenant_context.tenant_id
            or session.tenant_domain_id != tenant_context.tenant_domain_id
            or session.host != tenant_context.host
        ):
            raise InvalidSessionError()

        user = await self._users_repository.get_by_id(session.user_id)
        if user is None or user.tenant_id != tenant_context.tenant_id:
            raise InvalidSessionError()
        if not user.can_login():
            raise UserLoginUnavailableError()

        user.update_profile(
            last_name=dto.last_name,
            first_name=dto.first_name,
            middle_name=dto.middle_name,
            interface_language=dto.interface_language,
            interface_theme=dto.interface_theme,
            timezone=dto.timezone,
        )

        try:
            await self._users_repository.update_profile(user)
            await self._uow.commit()
        except Exception:
            await self._uow.rollback()
            raise

        return UpdateCurrentUserProfileResultDTO(
            id=user.id,
            status=user.status,
            last_name=user.last_name,
            first_name=user.first_name,
            middle_name=user.middle_name,
            avatar=user.avatar,
            interface_language=user.interface_language,
            interface_theme=user.interface_theme,
            timezone=user.timezone,
            emails=[
                GetCurrentUserEmailDTO(
                    id=email.id,
                    email=email.email,
                    is_primary=email.is_primary,
                    is_verified=email.is_verified,
                )
                for email in user.emails
                if not email.is_deleted
            ],
        )
