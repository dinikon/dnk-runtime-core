from __future__ import annotations
import sqlalchemy as sa
from src.modules.currency.application.provider.dto.provider_status_dto import (
    ProviderStatusDTO,
)
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.application.rate_import.dto.rate_import_dto import (
    RateImportDTO,
)
from src.modules.currency.domain.rate_import.value_object.id import RateImportIdVO
from src.modules.currency.infrastructure.persistence.exchange_rate.repository import (
    SqlRateReader,
)
from src.modules.currency.infrastructure.persistence.provider_rate.model import (
    ProviderRateModel,
)
from src.modules.currency.infrastructure.persistence.rate_import.model import (
    RateImportModel,
)


class SqlProviderRateRepository(SqlRateReader):
    """Persistence adapter for provider rate records."""

    @staticmethod
    def table(provider):
        return ProviderRateModel.__table__

    async def provider_status(self, provider: ProviderCode) -> ProviderStatusDTO:
        imports, rates = RateImportModel.__table__, ProviderRateModel.__table__
        last = (
            (
                await self.session.execute(
                    sa.select(imports)
                    .where(imports.c.provider_code == str(provider))
                    .order_by(imports.c.started_at.desc(), imports.c.id.desc())
                    .limit(1)
                )
            )
            .mappings()
            .first()
        )
        latest = await self.session.scalar(
            sa.select(sa.func.max(rates.c.effective_date)).where(
                rates.c.provider_code == str(provider), rates.c.is_current
            )
        )
        return ProviderStatusDTO(
            (
                RateImportDTO(
                    RateImportIdVO.from_value(last["id"]),
                    ProviderCode(last["provider_code"]),
                    last["started_at"],
                    last["finished_at"],
                    last["requested_date_from"],
                    last["requested_date_to"],
                    last["status"],
                    last["received_count"],
                    last["created_count"],
                    last["updated_count"],
                    last["error_count"],
                    last["error_message"],
                )
                if last
                else None
            ),
            latest,
        )


__all__ = ["SqlProviderRateRepository"]
