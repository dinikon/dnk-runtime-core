from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.crm.application.service.funnel_cards import FunnelCardsService
from src.modules.crm.infrastructure.lead.persistence.repository import (
    SqlAlchemyLeadRepository,
)
from src.modules.crm.infrastructure.deal.persistence.repository import (
    SqlAlchemyDealRepository,
)
from src.modules.crm.infrastructure.persistence.funnel_usage import (
    SqlAlchemyFunnelUsageQuery,
)
from src.modules.crm.infrastructure.persistence.position_history import (
    SqlAlchemyPositionHistory,
)


def get_funnel_cards_service(uow: UoWDep, uuid: UuidDep) -> FunnelCardsService:
    """Собирает контракт CRM на общей сессии внешнего UoW."""
    return FunnelCardsService(
        SqlAlchemyLeadRepository(uow.session),
        SqlAlchemyDealRepository(uow.session),
        SqlAlchemyFunnelUsageQuery(uow.session),
        SqlAlchemyPositionHistory(uow.session),
        uuid,
    )


FunnelCardsServiceDep = Annotated[FunnelCardsService, Depends(get_funnel_cards_service)]
