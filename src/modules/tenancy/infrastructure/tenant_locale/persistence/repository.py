from sqlalchemy import delete, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.tenancy.domain.tenant_locale.aggregate import TenantLocale
from src.modules.tenancy.domain.tenant_locale.error import (
    TenantLocaleAlreadySelectedError,
)
from src.modules.tenancy.domain.tenant_locale.value_object.code import (
    TenantLocaleCodeVO,
)
from src.modules.tenancy.infrastructure.tenant_locale.persistence.model import (
    TenantLocaleModel,
)


class SqlAlchemyTenantLocaleRepository:
    """Работает через общую сессию с уже привязанной tenant-схемой."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, locale: TenantLocale) -> None:
        """Добавляет выбор, полагаясь на PK при конкурентном добавлении."""
        try:
            await self._session.execute(
                insert(TenantLocaleModel).values(
                    code=locale.code.value,
                    created_at=locale.created_at,
                    created_by=locale.created_by.uuid,
                )
            )
        except IntegrityError as exc:
            original = exc.orig
            cause = original.__cause__
            constraint = getattr(original, "constraint_name", None) or getattr(
                cause, "constraint_name", None
            )
            if (
                getattr(original, "sqlstate", None) == "23505"
                and constraint == "pk_tenant_locales"
            ):
                raise TenantLocaleAlreadySelectedError(
                    "Locale is already selected."
                ) from exc
            raise

    async def remove(self, code: TenantLocaleCodeVO) -> bool:
        """Удаляет выбор локали, не затрагивая будущие таблицы переводов."""
        result = await self._session.execute(
            delete(TenantLocaleModel)
            .where(TenantLocaleModel.code == code.value)
            .returning(TenantLocaleModel.code)
        )
        return result.scalar_one_or_none() is not None
