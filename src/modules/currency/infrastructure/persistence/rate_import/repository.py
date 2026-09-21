from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.domain.rate_import.value_object.id import RateImportIdVO
from src.modules.currency.infrastructure.persistence.rate_import.model import (
    RateImportModel,
)


class SqlRateImportRepository:
    """Persist global import attempts without tenant events or autonomous commits."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def start(
        self,
        identifier: RateImportIdVO,
        provider: ProviderCode,
        start_date: date,
        end_date: date,
        now: datetime,
    ) -> None:
        await self.session.execute(
            sa.insert(RateImportModel.__table__).values(
                id=identifier.uuid,
                provider_code=str(provider),
                started_at=now,
                requested_date_from=start_date,
                requested_date_to=end_date,
                status="running",
                received_count=0,
                created_count=0,
                updated_count=0,
                error_count=0,
            )
        )

    async def finish(
        self,
        identifier: RateImportIdVO,
        *,
        status: str,
        now: datetime,
        received: int = 0,
        created: int = 0,
        updated: int = 0,
        error: str | None = None,
    ) -> None:
        table = RateImportModel.__table__
        await self.session.execute(
            sa.update(table)
            .where(table.c.id == identifier.uuid)
            .values(
                status=status,
                finished_at=now,
                received_count=received,
                created_count=created,
                updated_count=updated,
                error_count=int(error is not None),
                error_message=error,
            )
        )


__all__ = ["SqlRateImportRepository"]
