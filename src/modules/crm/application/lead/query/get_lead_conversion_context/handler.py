from src.modules.crm.application.lead.query.get_lead_conversion_context.query import (
    GetLeadConversionContextQuery,
)
from src.modules.crm.application.lead.query.get_lead_conversion_context.dto import (
    GetLeadConversionContextResultDTO,
)
from src.modules.crm.application.lead.service.conversion_preparation import (
    ConversionPreparationService,
)


class GetLeadConversionContextHandler:
    """Выполняет read-only подготовку формы конвертации."""

    def __init__(self, service: ConversionPreparationService) -> None:
        """Принимает прикладной сервис подготовки."""
        self._service = service

    async def execute(
        self, query: GetLeadConversionContextQuery
    ) -> GetLeadConversionContextResultDTO:
        """Возвращает конкретный согласованный context."""
        return await self._service.prepare(query.tenant_id, query.lead_id)
