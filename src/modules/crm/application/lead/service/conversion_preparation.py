import hashlib
import json
from dataclasses import asdict
from uuid import UUID
from src.modules.crm.application.lead.port.query_repository import (
    LeadQueryRepositoryProtocol,
)
from src.modules.crm.application.lead.port.basket import LeadBasketPort
from src.modules.crm.application.contact_point.port import ContactPointsPort
from src.modules.crm.application.contact.port.company_link_query_repository import (
    ContactCompanyQueryRepositoryProtocol,
)
from src.modules.crm.application.lead.query.get_lead_conversion_context.dto import (
    GetLeadConversionContextResultDTO,
)
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.domain.sales_error import SalesNotFoundError, SalesConflictError
from src.modules.crm.domain.lead.service.conversion_policy import MODES


class ConversionPreparationService:
    """Собирает read snapshot и fingerprint без скрытых изменений."""

    def __init__(
        self,
        leads: LeadQueryRepositoryProtocol,
        basket: LeadBasketPort,
        points: ContactPointsPort,
        companies: ContactCompanyQueryRepositoryProtocol,
    ) -> None:
        """Принимает необходимые read-контракты."""
        self._leads = leads
        self._basket = basket
        self._points = points
        self._companies = companies

    async def prepare(
        self, tenant_id: UUID, lead_id: UUID
    ) -> GetLeadConversionContextResultDTO:
        """Проверяет источник и вычисляет токен только используемого содержимого."""
        record = await self._leads.get(lead_id)
        if record is None:
            raise SalesNotFoundError("Лид не найден.")
        if record.conversion_result is not None:
            raise SalesConflictError("Лид уже конвертирован.")
        basket = await self._basket.get(lead_id)
        points = await self._points.list(EntityIdVO(tenant_id), EntityIdVO(lead_id))
        companies = (
            tuple(
                await self._companies.list_companies(ContactIdVO(record.contact_id))
                or ()
            )
            if record.contact_id
            else ()
        )
        source = {
            k: getattr(record, k)
            for k in (
                "id",
                "title",
                "first_name",
                "last_name",
                "middle_name",
                "company_name",
                "contact_id",
                "company_id",
            )
        }
        encoded = json.dumps(
            dict(
                record=source,
                basket=asdict(basket),
                points=asdict(points),
                companies=[asdict(c) for c in companies],
            ),
            sort_keys=True,
            default=str,
            ensure_ascii=False,
        )
        token = hashlib.sha256(encoded.encode()).hexdigest()
        return GetLeadConversionContextResultDTO(
            token, record, basket, points, companies, tuple(MODES)
        )
