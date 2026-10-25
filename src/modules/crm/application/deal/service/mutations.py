from dataclasses import asdict
from uuid import UUID
from src.modules.crm.domain.deal.aggregate import Deal
from src.modules.crm.domain.deal.repository import DealRepositoryProtocol
from src.modules.crm.domain.sales_error import SalesNotFoundError
from src.modules.crm.application.deal.port.basket import DealBasketPort
from src.modules.crm.application.port.funnel import FunnelPort
from src.modules.crm.application.service.participants import ParticipantsService
from src.modules.crm.application.contact_point.port import ContactPointsPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.crm.application.deal.command.create_deal.command import (
    CreateDealCommand,
)
from src.modules.crm.application.deal.command.update_deal.command import (
    UpdateDealCommand,
)
from src.modules.crm.application.deal.command.move_deal.command import MoveDealCommand
from src.modules.crm.application.deal.command.change_funnel_deal.command import (
    ChangeDealFunnelCommand,
)


class DealMutationService:
    """Общая orchestration сценариев Deal, без handler chains."""

    def __init__(
        self,
        repository: DealRepositoryProtocol,
        basket: DealBasketPort,
        funnels: FunnelPort,
        participants: ParticipantsService,
        points: ContactPointsPort,
        source_points: ContactPointsPort,
        uuid: UUIdGeneratorProtocol,
        clock: ClockPort,
    ) -> None:
        """Принимает порты одного внешнего UoW."""
        self.repository = repository
        self.basket = basket
        self.funnels = funnels
        self.participants = participants
        self.points = points
        self.source_points = source_points
        self.uuid = uuid
        self.clock = clock

    async def create(self, command: CreateDealCommand) -> tuple[Deal, dict[str, UUID]]:
        """Создаёт владельца, его корзину и points в общей транзакции."""
        position = await self.funnels.resolve("crm.deal", command.funnel_id)
        entity = Deal.create(
            record_id=EntityIdVO(self.uuid.new()),
            title=command.title,
            position=position,
            actor_id=EntityIdVO(command.actor_id),
            now=self.clock.now(),
        )
        await self.participants.validate(command.contact_ids, command.company_ids)
        entity.revise(
            fields=dict(
                contact_ids=command.contact_ids, company_ids=command.company_ids
            ),
            actor_id=EntityIdVO(command.actor_id),
            now=self.clock.now(),
        )
        phones = command.phones
        emails = command.emails
        await self.repository.add(entity)
        _, mapping = await self.basket.create(
            entity.id.uuid, command.tenant_id, command.basket, command.locale
        )
        await self.points.sync(
            EntityIdVO(command.tenant_id),
            EntityIdVO(command.actor_id),
            EntityIdVO(entity.id.uuid),
            phones,
            emails,
        )
        return entity, mapping

    async def _load(self, record_id: UUID) -> Deal:
        """Блокирует владельца до любых связанных изменений."""
        entity = await self.repository.get_for_update(EntityIdVO(record_id))
        if entity is None:
            raise SalesNotFoundError("Карточка не найдена.")
        entity.ensure_editable()
        return entity

    async def update(self, command: UpdateDealCommand) -> tuple[Deal, dict[str, UUID]]:
        """Проверяет ссылки, изменяет владельца, Basket и points атомарно."""
        entity = await self._load(command.record_id)
        await self.participants.validate(
            tuple(
                command.fields.get(
                    "contact_ids", tuple(i.uuid for i in entity.contact_ids)
                )
            ),
            tuple(
                command.fields.get(
                    "company_ids", tuple(i.uuid for i in entity.company_ids)
                )
            ),
        )
        entity.revise(
            fields=command.fields,
            actor_id=EntityIdVO(command.actor_id),
            now=self.clock.now(),
        )
        mapping = (
            await self.basket.replace(
                entity.id.uuid, command.tenant_id, command.basket, command.locale
            )
            if command.basket is not None
            else {}
        )
        if command.phones is not None or command.emails is not None:
            await self.points.sync(
                EntityIdVO(command.tenant_id),
                EntityIdVO(command.actor_id),
                EntityIdVO(entity.id.uuid),
                command.phones,
                command.emails,
            )
        if command.basket is not None:
            entity.touch(actor_id=EntityIdVO(command.actor_id), now=self.clock.now())
        await self.repository.save(entity)
        return entity, mapping

    async def move(self, command: MoveDealCommand) -> tuple[Deal, dict[str, UUID]]:
        """Перемещает только стадию текущего процесса."""
        entity = await self._load(command.record_id)
        selected = await self.funnels.resolve(
            "crm.deal", entity.position.funnel_id.uuid, command.stage_id
        )
        entity.move(
            funnel_id=selected.funnel_id,
            stage_id=selected.stage_id,
            expected_revision=command.expected_position_revision,
            actor_id=EntityIdVO(command.actor_id),
            now=self.clock.now(),
        )
        await self.repository.save(entity)
        return entity, {}

    async def change_funnel(
        self, command: ChangeDealFunnelCommand
    ) -> tuple[Deal, dict[str, UUID]]:
        """Явно переносит в первую стадию другой воронки."""
        entity = await self._load(command.record_id)
        if command.funnel_id == entity.position.funnel_id.uuid:
            selected = entity.position
        else:
            selected = await self.funnels.resolve("crm.deal", command.funnel_id)
        entity.move(
            funnel_id=selected.funnel_id,
            stage_id=selected.stage_id,
            expected_revision=command.expected_position_revision,
            actor_id=EntityIdVO(command.actor_id),
            now=self.clock.now(),
        )
        await self.repository.save(entity)
        return entity, {}
