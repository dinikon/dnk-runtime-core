import hashlib
import json
from dataclasses import asdict
from uuid import UUID
from src.modules.crm.application.lead.command.convert_lead.command import (
    ConvertLeadCommand,
    ConversionContactInput,
    ConversionCompanyInput,
    ConversionDealInput,
)
from src.modules.crm.application.lead.command.convert_lead.dto import (
    ConvertLeadResultDTO,
)
from src.modules.crm.application.lead.service.conversion_preparation import (
    ConversionPreparationService,
)
from src.modules.crm.application.basket.service.basket import BasketApplicationService
from src.modules.crm.application.service.participants import ParticipantsService
from src.modules.crm.application.port.funnel import FunnelPort
from src.modules.crm.application.contact_point.port import ContactPointsPort
from src.modules.crm.application.contact_point.dto import (
    ContactPointDraftDTO,
    ContactPointsDTO,
)
from src.modules.crm.domain.lead.repository import LeadRepositoryProtocol
from src.modules.crm.domain.deal.repository import DealRepositoryProtocol
from src.modules.crm.domain.contact.aggregate import ContactEntity
from src.modules.crm.domain.company.aggregate import CompanyEntity
from src.modules.crm.domain.deal.aggregate import Deal
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.domain.company.value_object.identifier import CompanyIdVO
from src.modules.crm.domain.contact.value_object.company_link import (
    ContactCompanyLinkVO,
)
from src.modules.crm.application.contact.port.company_link_repository import (
    CompanyLinkRepositoryProtocol,
)
from src.modules.crm.domain.lead.service.conversion_policy import LeadConversionPolicy
from src.modules.crm.domain.sales_error import (
    SalesConflictError,
    SalesError,
    SalesNotFoundError,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class ConvertLeadHandler:
    """Атомарно создаёт выбранные результаты, сохраняя исходный лид."""

    def __init__(
        self,
        leads: LeadRepositoryProtocol,
        deals: DealRepositoryProtocol,
        preparation: ConversionPreparationService,
        baskets: BasketApplicationService,
        participants: ParticipantsService,
        links: CompanyLinkRepositoryProtocol,
        funnels: FunnelPort,
        contact_points: ContactPointsPort,
        company_points: ContactPointsPort,
        deal_points: ContactPointsPort,
        uuid: UUIdGeneratorProtocol,
        clock: ClockPort,
    ) -> None:
        """Все репозитории и адаптеры собраны на общей сессии внешнего UoW."""
        self._leads = leads
        self._deals = deals
        self._preparation = preparation
        self._baskets = baskets
        self._participants = participants
        self._links = links
        self._funnels = funnels
        self._points = {
            "contact": contact_points,
            "company": company_points,
            "deal": deal_points,
        }
        self._uuid = uuid
        self._clock = clock

    async def _copy_points(
        self,
        tenant_id: UUID,
        actor_id: UUID,
        target: UUID,
        kind: str,
        selected: tuple[UUID, ...],
        source: ContactPointsDTO,
    ) -> None:
        """Создаёт новые bindings, не переносит ID исходных связей."""
        ids = set(selected)
        phones = tuple(
            ContactPointDraftDTO(
                p.value, label_id=p.label_id, country_code=p.country_code
            )
            for p in source.phones
            if p.binding_id in ids
        )
        emails = tuple(
            ContactPointDraftDTO(p.value, label_id=p.label_id)
            for p in source.emails
            if p.binding_id in ids
        )
        await self._points[kind].sync(
            EntityIdVO(tenant_id),
            EntityIdVO(actor_id),
            EntityIdVO(target),
            phones,
            emails,
        )

    async def execute(self, command: ConvertLeadCommand) -> ConvertLeadResultDTO:
        """Проверяет replay до frozen-состояния, затем создаёт всё в одной транзакции."""
        if not command.idempotency_key or len(command.idempotency_key) > 200:
            raise SalesError("Нужен Idempotency-Key до 200 символов.")
        payload = asdict(command)
        payload.pop("actor_id")
        payload.pop("idempotency_key")
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()
        lead = await self._leads.get_for_update(EntityIdVO(command.lead_id))
        if lead is None:
            raise SalesNotFoundError("Лид не найден.")
        if lead.conversion_result is not None:
            if (
                lead.conversion_key != command.idempotency_key
                or lead.conversion_fingerprint != fingerprint
            ):
                raise SalesConflictError("Лид уже конвертирован другим запросом.")
            return ConvertLeadResultDTO(**lead.conversion_result, replay=True)
        lead.ensure_editable()
        source_contact_id = lead.contact_id.uuid if lead.contact_id else None
        source_company_id = lead.company_id.uuid if lead.company_id else None
        source = await self._baskets.lock("crm.lead", lead.id.uuid)
        context = await self._preparation.prepare(command.tenant_id, lead.id.uuid)
        if (
            context.source_token != command.expected_source_token
            or source.revision != command.expected_basket_revision
        ):
            raise SalesConflictError(
                "Данные лида изменились. Обновите подготовку конвертации."
            )
        selections = {
            "contact": command.contact_points,
            "company": command.company_points,
            "deal": command.deal_points,
        }
        provided = {
            k for k in ("contact", "company", "deal") if getattr(command, k) is not None
        }
        additional = command.deal.additional_company_ids if command.deal else ()
        allowed = {c.id for c in context.available_companies}
        if source_company_id:
            allowed.add(source_company_id)
        policy_selections = {
            kind: tuple(EntityIdVO(value) for value in ids) if ids is not None else None
            for kind, ids in selections.items()
        }
        selected = LeadConversionPolicy.validate(
            command.mode,
            provided,
            policy_selections,
            {
                EntityIdVO(p.binding_id)
                for p in (*context.points.phones, *context.points.emails)
            },
            tuple(EntityIdVO(value) for value in additional),
            {EntityIdVO(value) for value in allowed},
        )
        now = self._clock.now()
        actor = EntityIdVO(command.actor_id)
        contact_id = self._uuid.new() if "contact" in selected else None
        company_id = self._uuid.new() if "company" in selected else None
        deal_id = self._uuid.new() if "deal" in selected else None
        if contact_id:
            draft = command.contact or ConversionContactInput(
                lead.first_name or "", lead.last_name, lead.middle_name
            )
            entity = ContactEntity.create(
                contact_id=ContactIdVO(contact_id),
                actor_id=actor,
                now=now,
                **asdict(draft),
            )
            await self._participants.contacts.add(entity)
        if company_id:
            draft = command.company or ConversionCompanyInput(lead.company_name or "")
            entity = CompanyEntity.create(
                company_id=CompanyIdVO(company_id),
                legal_name=draft.legal_name,
                actor_id=actor,
                now=now,
            )
            await self._participants.companies.add(entity)
        # Проверка существующих ссылок отделена от создания новых участников.
        await self._participants.validate(
            (source_contact_id,) if source_contact_id else (),
            tuple(
                sorted(
                    set(additional)
                    | ({source_company_id} if source_company_id else set()),
                    key=str,
                )
            ),
        )
        pairs = set()
        if contact_id and company_id:
            pairs.add((contact_id, company_id))
        for link in command.links:
            c = link.contact_id or contact_id
            k = link.company_id or company_id
            if c is None or k is None or (c != contact_id and k != company_id):
                raise SalesError(
                    "Связь должна включать хотя бы один создаваемый объект."
                )
            if c != contact_id and c != source_contact_id:
                raise SalesError("Недопустимый контакт связи.")
            if k != company_id and k not in ({source_company_id} | set(additional)):
                raise SalesError("Недопустимая компания связи.")
            pairs.add((c, k))
        for c, k in sorted(pairs, key=lambda pair: (str(pair[0]), str(pair[1]))):
            await self._links.link(ContactCompanyLinkVO(ContactIdVO(c), CompanyIdVO(k)))
        basket_id = None
        if deal_id:
            draft = command.deal or ConversionDealInput(lead.title)
            position = await self._funnels.resolve("crm.deal", draft.funnel_id)
            deal = Deal.create(
                record_id=EntityIdVO(deal_id),
                title=draft.title,
                position=position,
                actor_id=EntityIdVO(command.actor_id),
                now=now,
            )
            contacts = tuple(
                sorted({i for i in (contact_id, source_contact_id) if i}, key=str)
            )
            companies = tuple(
                sorted(
                    set(additional) | {i for i in (company_id, source_company_id) if i},
                    key=str,
                )
            )
            deal.revise(
                fields={"contact_ids": contacts, "company_ids": companies},
                actor_id=EntityIdVO(command.actor_id),
                now=now,
            )
            deal.set_lead_origin(
                lead.id,
                {
                    k: getattr(lead, k)
                    for k in (
                        "title",
                        "first_name",
                        "last_name",
                        "middle_name",
                        "company_name",
                    )
                },
            )
            await self._deals.add(deal)
            basket_id = await self._baskets.copy(source, deal_id)
        for kind, target in (
            ("contact", contact_id),
            ("company", company_id),
            ("deal", deal_id),
        ):
            if target:
                await self._copy_points(
                    command.tenant_id,
                    command.actor_id,
                    target,
                    kind,
                    selections[kind],
                    context.points,
                )
        result = ConvertLeadResultDTO(
            str(self._uuid.new()),
            command.mode,
            str(contact_id) if contact_id else None,
            str(company_id) if company_id else None,
            str(deal_id) if deal_id else None,
            str(basket_id) if basket_id else None,
            now.isoformat(),
            str(command.actor_id),
        )
        stored = asdict(result)
        stored.pop("replay")
        lead.complete_conversion(
            result=stored,
            key=command.idempotency_key,
            fingerprint=fingerprint,
            actor_id=EntityIdVO(command.actor_id),
            now=now,
        )
        await self._baskets.freeze(source)
        await self._leads.save(lead)
        return result
