from src.modules.crm.infrastructure.persistence.position_history import (
    SqlAlchemyPositionHistory,
)
from dataclasses import dataclass
from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.catalog.presentation.catalog_item.depends import (
    GetCatalogItemHandlerDep,
)
from src.modules.contact_points.presentation.depends.binding import (
    GetTargetsContactPointsHandlerDep,
    SyncTargetContactPointsHandlerDep,
    RemoveTargetContactPointsHandlerDep,
)
from src.modules.crm.infrastructure.contact_point.adapter import ContactPointsAdapter
from src.modules.crm.infrastructure.contact.persistence.repository import (
    SqlAlchemyContactRepository,
)
from src.modules.crm.infrastructure.company.persistence.repository import (
    SqlAlchemyCompanyRepository,
)
from src.modules.crm.infrastructure.contact.persistence.company_link_repository import (
    SqlAlchemyCompanyLinkRepository,
)
from src.modules.crm.infrastructure.contact.persistence.company_link_query_repository import (
    SqlAlchemyContactCompanyQueryRepository,
)
from src.modules.crm.infrastructure.basket.persistence.repository import (
    SqlAlchemyBasketRepository,
)
from src.modules.crm.infrastructure.basket.persistence.query_repository import (
    SqlAlchemyBasketQueryRepository,
)
from src.modules.crm.infrastructure.adapter.catalog_selection import (
    CatalogSelectionAdapter,
)
from src.modules.crm.infrastructure.adapter.funnel import FunnelAdapter
from src.modules.crm.application.basket.service.basket import BasketApplicationService
from src.modules.crm.application.service.participants import ParticipantsService
from src.modules.crm.application.lead.service.conversion_preparation import (
    ConversionPreparationService,
)
from src.modules.crm.application.lead.command.convert_lead.handler import (
    ConvertLeadHandler,
)
from src.modules.crm.application.lead.query.get_lead_conversion_context.handler import (
    GetLeadConversionContextHandler,
)
from src.modules.funnel.application.service.resolve_stage import (
    ResolveFunnelStageService,
)
from src.modules.funnel.infrastructure.persistence.repository import (
    SqlAlchemyFunnelRepository,
)
from src.modules.crm.infrastructure.lead.persistence.repository import (
    SqlAlchemyLeadRepository,
)
from src.modules.crm.infrastructure.lead.persistence.query_repository import (
    SqlAlchemyLeadQueryRepository,
)
from src.modules.crm.infrastructure.lead.adapter.basket import LeadBasketAdapter
from src.modules.crm.application.lead.service.mutations import LeadMutationService
from src.modules.crm.application.lead.command.create_lead.handler import (
    CreateLeadHandler,
)
from src.modules.crm.application.lead.command.update_lead.handler import (
    UpdateLeadHandler,
)
from src.modules.crm.application.lead.command.move_lead.handler import MoveLeadHandler
from src.modules.crm.application.lead.command.change_funnel_lead.handler import (
    ChangeLeadFunnelHandler,
)
from src.modules.crm.application.lead.query.get_lead.handler import GetLeadHandler
from src.modules.crm.application.lead.query.list_leads.handler import ListLeadsHandler
from src.modules.crm.infrastructure.deal.persistence.repository import (
    SqlAlchemyDealRepository,
)
from src.modules.crm.infrastructure.deal.persistence.query_repository import (
    SqlAlchemyDealQueryRepository,
)
from src.modules.crm.infrastructure.deal.adapter.basket import DealBasketAdapter
from src.modules.crm.application.deal.service.mutations import DealMutationService
from src.modules.crm.application.deal.command.create_deal.handler import (
    CreateDealHandler,
)
from src.modules.crm.application.deal.command.update_deal.handler import (
    UpdateDealHandler,
)
from src.modules.crm.application.deal.command.move_deal.handler import MoveDealHandler
from src.modules.crm.application.deal.command.change_funnel_deal.handler import (
    ChangeDealFunnelHandler,
)
from src.modules.crm.application.deal.query.get_deal.handler import GetDealHandler
from src.modules.crm.application.deal.query.list_deals.handler import ListDealsHandler


@dataclass(slots=True)
class SalesDependencies:
    """Только внешняя сборка; инфраструктура не выходит в Application."""

    lead_mutations: LeadMutationService
    deal_mutations: DealMutationService
    lead_reader: SqlAlchemyLeadQueryRepository
    deal_reader: SqlAlchemyDealQueryRepository
    lead_basket: LeadBasketAdapter
    deal_basket: DealBasketAdapter
    lead_points: ContactPointsAdapter
    deal_points: ContactPointsAdapter
    converter: ConvertLeadHandler
    preparation: ConversionPreparationService


def get_sales_dependencies(
    uow: UoWDep,
    clock: ClockDep,
    uuid: UuidDep,
    catalog_reader: GetCatalogItemHandlerDep,
    point_reader: GetTargetsContactPointsHandlerDep,
    point_writer: SyncTargetContactPointsHandlerDep,
    point_remover: RemoveTargetContactPointsHandlerDep,
) -> SalesDependencies:
    """Собирает все участники атомарных сценариев на одной сессии."""
    session = uow.session
    history = SqlAlchemyPositionHistory(session)

    def points(key: str) -> ContactPointsAdapter:
        """Фиксирует доверенный target владельца при сборке."""
        return ContactPointsAdapter(
            key, point_reader, point_writer, point_remover, uuid
        )

    contact_points = points("crm.contact")
    company_points = points("crm.company")
    lead_points = points("crm.lead")
    deal_points = points("crm.deal")
    leads = SqlAlchemyLeadRepository(session)
    deals = SqlAlchemyDealRepository(session)
    lead_reader = SqlAlchemyLeadQueryRepository(session)
    deal_reader = SqlAlchemyDealQueryRepository(session)
    baskets = BasketApplicationService(
        SqlAlchemyBasketRepository(session),
        SqlAlchemyBasketQueryRepository(session),
        CatalogSelectionAdapter(catalog_reader),
        uuid,
    )
    lead_basket = LeadBasketAdapter(baskets)
    deal_basket = DealBasketAdapter(baskets)
    company_links = SqlAlchemyCompanyLinkRepository(session)
    links_reader = SqlAlchemyContactCompanyQueryRepository(session)
    participants = ParticipantsService(
        SqlAlchemyContactRepository(session),
        SqlAlchemyCompanyRepository(session),
        links_reader,
    )
    funnels = FunnelAdapter(
        ResolveFunnelStageService(SqlAlchemyFunnelRepository(session))
    )
    lead_mutations = LeadMutationService(
        leads,
        lead_basket,
        funnels,
        participants,
        lead_points,
        contact_points,
        uuid,
        clock,
        history,
    )
    deal_mutations = DealMutationService(
        deals,
        deal_basket,
        funnels,
        participants,
        deal_points,
        contact_points,
        uuid,
        clock,
        history,
    )
    preparation = ConversionPreparationService(
        lead_reader, lead_basket, lead_points, links_reader
    )
    converter = ConvertLeadHandler(
        leads,
        deals,
        preparation,
        baskets,
        participants,
        company_links,
        funnels,
        contact_points,
        company_points,
        deal_points,
        uuid,
        clock,
        history,
    )
    return SalesDependencies(
        lead_mutations,
        deal_mutations,
        lead_reader,
        deal_reader,
        lead_basket,
        deal_basket,
        lead_points,
        deal_points,
        converter,
        preparation,
    )


SalesDependenciesDep = Annotated[SalesDependencies, Depends(get_sales_dependencies)]


def get_create_lead_handler(deps: SalesDependenciesDep) -> CreateLeadHandler:
    """Собирает отдельный обработчик CreateLead."""
    return CreateLeadHandler(deps.lead_mutations)


CreateLeadHandlerDep = Annotated[CreateLeadHandler, Depends(get_create_lead_handler)]


def get_update_lead_handler(deps: SalesDependenciesDep) -> UpdateLeadHandler:
    """Собирает отдельный обработчик UpdateLead."""
    return UpdateLeadHandler(deps.lead_mutations)


UpdateLeadHandlerDep = Annotated[UpdateLeadHandler, Depends(get_update_lead_handler)]


def get_move_lead_handler(deps: SalesDependenciesDep) -> MoveLeadHandler:
    """Собирает отдельный обработчик MoveLead."""
    return MoveLeadHandler(deps.lead_mutations)


MoveLeadHandlerDep = Annotated[MoveLeadHandler, Depends(get_move_lead_handler)]


def get_change_funnel_lead_handler(
    deps: SalesDependenciesDep,
) -> ChangeLeadFunnelHandler:
    """Собирает отдельный обработчик ChangeLeadFunnel."""
    return ChangeLeadFunnelHandler(deps.lead_mutations)


ChangeLeadFunnelHandlerDep = Annotated[
    ChangeLeadFunnelHandler, Depends(get_change_funnel_lead_handler)
]


def get_get_lead_handler(deps: SalesDependenciesDep) -> GetLeadHandler:
    """Собирает отдельный обработчик GetLead."""
    return GetLeadHandler(deps.lead_reader, deps.lead_basket, deps.lead_points)


GetLeadHandlerDep = Annotated[GetLeadHandler, Depends(get_get_lead_handler)]


def get_list_lead_handler(deps: SalesDependenciesDep) -> ListLeadsHandler:
    """Собирает отдельный обработчик ListLeads."""
    return ListLeadsHandler(deps.lead_reader, deps.lead_basket, deps.lead_points)


ListLeadsHandlerDep = Annotated[ListLeadsHandler, Depends(get_list_lead_handler)]


def get_create_deal_handler(deps: SalesDependenciesDep) -> CreateDealHandler:
    """Собирает отдельный обработчик CreateDeal."""
    return CreateDealHandler(deps.deal_mutations)


CreateDealHandlerDep = Annotated[CreateDealHandler, Depends(get_create_deal_handler)]


def get_update_deal_handler(deps: SalesDependenciesDep) -> UpdateDealHandler:
    """Собирает отдельный обработчик UpdateDeal."""
    return UpdateDealHandler(deps.deal_mutations)


UpdateDealHandlerDep = Annotated[UpdateDealHandler, Depends(get_update_deal_handler)]


def get_move_deal_handler(deps: SalesDependenciesDep) -> MoveDealHandler:
    """Собирает отдельный обработчик MoveDeal."""
    return MoveDealHandler(deps.deal_mutations)


MoveDealHandlerDep = Annotated[MoveDealHandler, Depends(get_move_deal_handler)]


def get_change_funnel_deal_handler(
    deps: SalesDependenciesDep,
) -> ChangeDealFunnelHandler:
    """Собирает отдельный обработчик ChangeDealFunnel."""
    return ChangeDealFunnelHandler(deps.deal_mutations)


ChangeDealFunnelHandlerDep = Annotated[
    ChangeDealFunnelHandler, Depends(get_change_funnel_deal_handler)
]


def get_get_deal_handler(deps: SalesDependenciesDep) -> GetDealHandler:
    """Собирает отдельный обработчик GetDeal."""
    return GetDealHandler(deps.deal_reader, deps.deal_basket, deps.deal_points)


GetDealHandlerDep = Annotated[GetDealHandler, Depends(get_get_deal_handler)]


def get_list_deal_handler(deps: SalesDependenciesDep) -> ListDealsHandler:
    """Собирает отдельный обработчик ListDeals."""
    return ListDealsHandler(deps.deal_reader, deps.deal_basket, deps.deal_points)


ListDealsHandlerDep = Annotated[ListDealsHandler, Depends(get_list_deal_handler)]


def get_convert_lead_handler(deps: SalesDependenciesDep) -> ConvertLeadHandler:
    """Возвращает собранный атомарный сценарий."""
    return deps.converter


ConvertLeadHandlerDep = Annotated[ConvertLeadHandler, Depends(get_convert_lead_handler)]


def get_conversion_context_handler(
    deps: SalesDependenciesDep,
) -> GetLeadConversionContextHandler:
    """Собирает отдельный read-only handler."""
    return GetLeadConversionContextHandler(deps.preparation)


GetLeadConversionContextHandlerDep = Annotated[
    GetLeadConversionContextHandler, Depends(get_conversion_context_handler)
]
