from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.modules.communication.application.message_template.dto import (
    MessageTemplateDTO,
)
from src.modules.communication.application.message_template.query import (
    MessageTemplateQueryRepositoryProtocol,
)
from src.modules.communication.domain.message_template import (
    MessageTemplateIdVO,
    TemplateVersionStatusVO,
)
from src.modules.communication.infrastructure.message_template.row_mapper import (
    as_uuid,
    message_template_dto,
)
from src.modules.communication.infrastructure.runtime_object_names import (
    _TEMPLATE,
    _TEMPLATE_VERSION,
)
from src.modules.runtime_data.application.models import PageSpec, SortSpec
from src.modules.runtime_data.application.ports import RuntimeQueryGateway
from src.modules.runtime_data.application.query.typed_filter_builder import (
    RuntimeTypedFilterBuilder,
)
from src.modules.schema_registry.runtime import RuntimeObjectResolverProtocol
from src.modules.shared import EntityIdVO


class MessageTemplateQueryRuntimeRepository(MessageTemplateQueryRepositoryProtocol):
    """Query repository message templates поверх runtime_data query port."""

    def __init__(
        self,
        *,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        runtime_query_gateway: RuntimeQueryGateway,
    ) -> None:
        """Инициализирует query repository resolver-ом и runtime query gateway."""
        self._runtime_object_resolver = runtime_object_resolver
        self._runtime_query_gateway = runtime_query_gateway
        self._filter_builder = RuntimeTypedFilterBuilder()

    async def list_templates(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> list[MessageTemplateDTO]:
        """Возвращает список MessageTemplateDTO с active version metadata."""
        descriptor = await self._resolve_descriptor(tenant_id, _TEMPLATE)
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            sorting=(SortSpec("template_code"),),
        )
        result = []
        for row in rows:
            active_version = await self._load_active_template_version_row(
                tenant_id=tenant_id,
                template_id=MessageTemplateIdVO.from_value(as_uuid(row.get("id"))),
            )
            result.append(
                message_template_dto(
                    tenant_id=tenant_id,
                    row=row,
                    active_version=active_version,
                )
            )
        return result

    async def _load_active_template_version_row(
        self,
        *,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
    ) -> Mapping[str, Any] | None:
        """Загружает runtime row активной версии шаблона."""
        descriptor = await self._resolve_descriptor(tenant_id, _TEMPLATE_VERSION)
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="template_id",
                    op="eq",
                    value=template_id.uuid,
                ),
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="status",
                    op="eq",
                    value=TemplateVersionStatusVO.ACTIVE.value,
                ),
            ),
            page=PageSpec(limit=1, offset=0),
        )
        return rows[0] if rows else None

    async def _resolve_descriptor(self, tenant_id: EntityIdVO, object_name: str):
        """Получает runtime descriptor communication-объекта для tenant."""
        return await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=object_name,
        )


__all__ = ["MessageTemplateQueryRuntimeRepository"]
