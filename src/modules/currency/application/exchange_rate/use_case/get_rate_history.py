from src.modules.currency.application.exchange_rate.dto.rate_record_dto import (
    RateRecordDTO,
)
from src.modules.currency.application.exchange_rate.query.get_rate_history_query import (
    GetRateHistoryQuery,
)
from src.modules.currency.domain.exchange_rate.repository import RateRepository


class GetRateHistoryUseCase:
    """Execute the get rate history read scenario."""

    def __init__(self, repository: RateRepository):
        self.repository = repository

    async def __call__(self, query: GetRateHistoryQuery) -> tuple[RateRecordDTO, ...]:
        return tuple(
            RateRecordDTO.from_entity(r)
            for r in await self.repository.history(
                tenant_id=query.tenant_id,
                provider=query.provider,
                pair=query.pair,
                limit=query.limit,
                offset=query.offset,
            )
        )


__all__ = ["GetRateHistoryUseCase"]
