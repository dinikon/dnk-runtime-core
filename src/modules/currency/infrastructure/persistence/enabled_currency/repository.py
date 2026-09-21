from datetime import datetime
from sqlalchemy.dialects.postgresql import insert as pg_insert
import sqlalchemy as sa
from src.modules.currency.infrastructure.persistence.enabled_currency.model import (
    EnabledCurrencyModel,
)
from src.modules.currency.infrastructure.persistence.scoped_repository import (
    ScopedRepository,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO as Code
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SqlEnabledCurrencyRepository(ScopedRepository):
    """Read and update allowed currencies within the caller's tenant transaction."""

    async def enabled(self, *, tenant_id: EntityIdVO) -> set[CurrencyCodeVO]:
        table = EnabledCurrencyModel.__table__
        return {
            Code(code)
            for code in (
                await self.session.execute(
                    self.scoped(
                        sa.select(table.c.currency_code).where(table.c.enabled),
                        tenant_id,
                    )
                )
            ).scalars()
        }

    async def set_enabled(
        self,
        *,
        tenant_id: EntityIdVO,
        code: CurrencyCodeVO,
        enabled: bool,
        now: datetime,
    ) -> None:
        table = EnabledCurrencyModel.__table__
        statement = pg_insert(table).values(
            currency_code=str(code), enabled=enabled, created_at=now, updated_at=now
        )
        await self.session.execute(
            self.scoped(
                statement.on_conflict_do_update(
                    index_elements=[table.c.currency_code],
                    set_=dict(enabled=enabled, updated_at=now),
                ),
                tenant_id,
            )
        )


__all__ = ["SqlEnabledCurrencyRepository"]
