from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.identity.application.user.query.get_current_user.record_dto import (
    GetCurrentUserRecordDTO,
)
from src.modules.identity.domain.user.value_object.user_id import UserIdVO
from src.modules.identity.infrastructure.persistence.models.user import UserModel
from src.modules.identity.infrastructure.persistence.models.user_email import (
    UserEmailModel,
)
from src.modules.identity.infrastructure.user.persistence.query_mapper import (
    UserProfileQueryMapper,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    require_tenant_schema,
)


class SqlAlchemyUserProfileQueryRepository:
    """Читает профиль одной SQL-проекцией на заранее привязанной tenant-сессии."""

    def __init__(self, session: AsyncSession, naming: TenantSchemaNaming) -> None:
        """Получает общую сессию внешнего UoW и правило проверки его контекста."""
        self._session = session
        self._naming = naming

    async def get_current_user(
        self, user_id: UserIdVO, *, tenant_id: EntityIdVO
    ) -> GetCurrentUserRecordDTO | None:
        """Возвращает профиль с живыми emails без восстановления агрегата User."""
        await require_tenant_schema(
            await self._session.connection(), tenant_id.uuid, self._naming
        )
        users, emails = UserModel.__table__, UserEmailModel.__table__
        statement = (
            select(
                users.c.id,
                users.c.status,
                users.c.role,
                users.c.last_name,
                users.c.first_name,
                users.c.middle_name,
                users.c.avatar,
                users.c.interface_language,
                users.c.interface_theme,
                users.c.timezone,
                users.c.display_currency,
                emails.c.id.label("email_id"),
                emails.c.email,
                emails.c.is_primary,
                emails.c.is_verified,
            )
            .select_from(
                users.outerjoin(
                    emails,
                    and_(
                        emails.c.user_id == users.c.id, emails.c.is_deleted.is_(False)
                    ),
                )
            )
            .where(users.c.id == user_id.uuid, users.c.status == "active")
            .order_by(emails.c.id)
        )
        rows = (await self._session.execute(statement)).mappings().all()
        return None if not rows else UserProfileQueryMapper.to_current_user(rows)
