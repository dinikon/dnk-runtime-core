from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.funnel.infrastructure.persistence.repository import (
    SqlAlchemyFunnelRepository,
)
from src.modules.funnel.infrastructure.persistence.query_repository import (
    SqlAlchemyFunnelQueryRepository,
)
from src.modules.funnel.application.command.create_funnel.handler import (
    CreateFunnelHandler,
)


def get_create_funnel_handler(
    uow: UoWDep, uuid: UuidDep, clock: ClockDep
) -> CreateFunnelHandler:
    """Собирает CreateFunnel на общей сессии tenant."""
    return CreateFunnelHandler(SqlAlchemyFunnelRepository(uow.session), uuid, clock)


CreateFunnelHandlerDep = Annotated[
    CreateFunnelHandler, Depends(get_create_funnel_handler)
]
from src.modules.funnel.application.command.update_funnel.handler import (
    UpdateFunnelHandler,
)


def get_update_funnel_handler(
    uow: UoWDep, uuid: UuidDep, clock: ClockDep
) -> UpdateFunnelHandler:
    """Собирает UpdateFunnel на общей сессии tenant."""
    return UpdateFunnelHandler(SqlAlchemyFunnelRepository(uow.session), uuid, clock)


UpdateFunnelHandlerDep = Annotated[
    UpdateFunnelHandler, Depends(get_update_funnel_handler)
]
from src.modules.funnel.application.query.get_funnel.handler import GetFunnelHandler


def get_get_funnel_handler(uow: UoWDep) -> GetFunnelHandler:
    """Собирает GetFunnel на общей сессии tenant."""
    return GetFunnelHandler(SqlAlchemyFunnelQueryRepository(uow.session))


GetFunnelHandlerDep = Annotated[GetFunnelHandler, Depends(get_get_funnel_handler)]
from src.modules.funnel.application.query.list_funnels.handler import ListFunnelsHandler


def get_list_funnels_handler(uow: UoWDep) -> ListFunnelsHandler:
    """Собирает ListFunnels на общей сессии tenant."""
    return ListFunnelsHandler(SqlAlchemyFunnelQueryRepository(uow.session))


ListFunnelsHandlerDep = Annotated[ListFunnelsHandler, Depends(get_list_funnels_handler)]
