from dataclasses import asdict
from uuid import UUID
from src.modules.crm.domain.lead.aggregate import Lead
from src.modules.crm.domain.lead.repository import LeadRepositoryProtocol
from src.modules.crm.domain.sales_error import SalesNotFoundError
from src.modules.crm.application.lead.port.basket import LeadBasketPort
from src.modules.crm.application.port.funnel import FunnelPort
from src.modules.crm.application.service.participants import ParticipantsService
from src.modules.crm.application.contact_point.port import ContactPointsPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.crm.application.lead.command.create_lead.command import (
    CreateLeadCommand,
)
from src.modules.crm.application.lead.command.update_lead.command import (
    UpdateLeadCommand,
)
from src.modules.crm.application.lead.command.move_lead.command import MoveLeadCommand
from src.modules.crm.application.lead.command.change_funnel_lead.command import (
    ChangeLeadFunnelCommand,
)


class LeadMutationService:
    """Общая orchestration сценариев Lead, без handler chains."""

    def __init__(
        self,
        repository: LeadRepositoryProtocol,
        basket: LeadBasketPort,
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

    async def create(self, command: CreateLeadCommand) -> tuple[Lead, dict[str, UUID]]:
        """Создаёт владельца, его корзину и points в общей транзакции."""
        position = await self.funnels.resolve("crm.lead", command.funnel_id)
        entity = Lead.create(
            record_id=EntityIdVO(self.uuid.new()),
            title=command.title,
            position=position,
            actor_id=EntityIdVO(command.actor_id),
            now=self.clock.now(),
        )
        fields = {
            k: getattr(command, k)
            for k in (
                "first_name",
                "last_name",
                "middle_name",
                "company_name",
                "contact_id",
                "company_id",
            )
        }
        phones = command.phones
        emails = command.emails
        if command.contact_id:
            snapshot = await self.participants.contact(command.contact_id)
            # Согласованный UI передаёт явные overrides; снимок заполняет отсутствующие части.
            for key, value in asdict(snapshot).items():
                if fields[key] is None and key not in command.contact_overrides:
                    fields[key] = value
            source = await self.source_points.list(
                EntityIdVO(command.tenant_id), EntityIdVO(command.contact_id)
            )
            from src.modules.crm.application.contact_point.dto import (
                ContactPointDraftDTO,
            )

            if phones is None:
                phones = tuple(
                    ContactPointDraftDTO(
                        p.value, label_id=p.label_id, country_code=p.country_code
                    )
                    for p in source.phones
                )
            if emails is None:
                emails = tuple(
                    ContactPointDraftDTO(p.value, label_id=p.label_id)
                    for p in source.emails
                )
        await self.participants.validate(
            (command.contact_id,) if command.contact_id else (),
            (command.company_id,) if command.company_id else (),
        )
        entity.revise(
            fields=fields, actor_id=EntityIdVO(command.actor_id), now=self.clock.now()
        )
        await self.repository.add(entity)
        _, mapping = await self.basket.create(
            entity.id.uuid, command.tenant_id, command.basket, command.locale
        )
        await self.points.sync(
            EntityIdVO(command.tenant_id),
            EntityIdVO(command.actor_id),
            EntityIdVO(entity.id.uuid),
            phones or (),
            emails or (),
        )
        return entity, mapping

    async def _load(self, record_id: UUID) -> Lead:
        """Блокирует владельца до любых связанных изменений."""
        entity = await self.repository.get_for_update(EntityIdVO(record_id))
        if entity is None:
            raise SalesNotFoundError("Карточка не найдена.")
        entity.ensure_editable()
        return entity

    async def update(self, command: UpdateLeadCommand) -> tuple[Lead, dict[str, UUID]]:
        """Проверяет ссылки, изменяет владельца, Basket и points атомарно."""
        entity = await self._load(command.record_id)
        contact_id = command.fields.get(
            "contact_id", entity.contact_id.uuid if entity.contact_id else None
        )
        company_id = command.fields.get(
            "company_id", entity.company_id.uuid if entity.company_id else None
        )
        await self.participants.validate(
            (contact_id,) if contact_id else (), (company_id,) if company_id else ()
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
        if (
            command.basket is not None
            or command.phones is not None
            or command.emails is not None
        ):
            entity.touch(actor_id=EntityIdVO(command.actor_id), now=self.clock.now())
        await self.repository.save(entity)
        return entity, mapping

    async def move(self, command: MoveLeadCommand) -> tuple[Lead, dict[str, UUID]]:
        """Перемещает только стадию текущего процесса."""
        entity = await self._load(command.record_id)
        selected = await self.funnels.resolve(
            "crm.lead", entity.position.funnel_id.uuid, command.stage_id
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
        self, command: ChangeLeadFunnelCommand
    ) -> tuple[Lead, dict[str, UUID]]:
        """Явно переносит в первую стадию другой воронки."""
        entity = await self._load(command.record_id)
        if command.funnel_id == entity.position.funnel_id.uuid:
            selected = entity.position
        else:
            selected = await self.funnels.resolve("crm.lead", command.funnel_id)
        entity.move(
            funnel_id=selected.funnel_id,
            stage_id=selected.stage_id,
            expected_revision=command.expected_position_revision,
            actor_id=EntityIdVO(command.actor_id),
            now=self.clock.now(),
        )
        await self.repository.save(entity)
        return entity, {}
