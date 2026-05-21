from __future__ import annotations

from src.modules.communication.domain.message_template import (
    MessageTemplateCodeVO,
    MessageTemplateEntity,
    MessageTemplateIdVO,
    MessageTemplateProviderLookupProtocol,
    MessageTemplateRepositoryProtocol,
    TemplateVersionEntity,
    TemplateVersionIdVO,
)
from src.modules.communication.domain.provider_connector import (
    ProviderConnector,
    ProviderConnectorIdVO,
    ProviderMessageType,
    ProviderMessageTypeIdVO,
)
from src.modules.communication.infrastructure.message_template.row_mapper import (
    message_template_entity,
    provider_connector_entity,
    provider_message_type_entity,
    template_version_entity,
)
from src.modules.communication.infrastructure.runtime_object_names import (
    _CONNECTOR,
    _MESSAGE_TYPE,
    _TEMPLATE,
    _TEMPLATE_VERSION,
)
from src.modules.runtime_data.application.models import PageSpec, SortSpec
from src.modules.runtime_data.application.ports import (
    RuntimeCommandGateway,
    RuntimeQueryGateway,
)
from src.modules.runtime_data.application.query.typed_filter_builder import (
    RuntimeTypedFilterBuilder,
)
from src.modules.schema_registry.runtime import RuntimeObjectResolverProtocol
from src.modules.shared import EntityIdVO


class MessageTemplateRuntimeRepository(
    MessageTemplateRepositoryProtocol,
    MessageTemplateProviderLookupProtocol,
):
    """Domain repository message template aggregate поверх runtime_data ports."""

    def __init__(
        self,
        *,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        runtime_command_gateway: RuntimeCommandGateway,
        runtime_query_gateway: RuntimeQueryGateway,
    ) -> None:
        """Инициализирует repository resolver-ом descriptor и runtime gateways."""
        self._runtime_object_resolver = runtime_object_resolver
        self._runtime_command_gateway = runtime_command_gateway
        self._runtime_query_gateway = runtime_query_gateway
        self._filter_builder = RuntimeTypedFilterBuilder()

    async def load_template(
        self,
        *,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
    ) -> MessageTemplateEntity | None:
        """Загружает message template entity из runtime-таблицы tenant."""
        descriptor = await self._resolve_descriptor(tenant_id, _TEMPLATE)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=template_id.uuid,
        )
        if row is None:
            return None
        return message_template_entity(tenant_id=tenant_id, row=row)

    async def load_template_by_code(
        self,
        *,
        tenant_id: EntityIdVO,
        template_code: MessageTemplateCodeVO,
    ) -> MessageTemplateEntity | None:
        """Загружает message template entity по tenant-local code."""
        descriptor = await self._resolve_descriptor(tenant_id, _TEMPLATE)
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="template_code",
                    op="eq",
                    value=template_code.value,
                ),
            ),
            page=PageSpec(limit=1, offset=0),
        )
        if not rows:
            return None
        return message_template_entity(tenant_id=tenant_id, row=rows[0])

    async def save_template(
        self,
        *,
        tenant_id: EntityIdVO,
        template: MessageTemplateEntity,
    ) -> MessageTemplateEntity:
        """Создает или обновляет runtime-строку шаблона и возвращает entity."""
        descriptor = await self._resolve_descriptor(tenant_id, _TEMPLATE)
        existing = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=template.template_id.uuid,
        )
        payload = {
            "template_code": template.template_code.value,
            "name": template.name.value,
            "description": template.description,
            "provider_connector_id": template.provider_connector_id.uuid,
            "provider_message_type_id": template.provider_message_type_id.uuid,
            "channel_code": template.channel_code.value,
            "message_class": template.message_class.value,
            "status": template.status.value,
        }
        if existing is None:
            row = await self._runtime_command_gateway.insert(
                descriptor=descriptor,
                payload={
                    "id": template.template_id.uuid,
                    **payload,
                },
            )
        else:
            row = await self._runtime_command_gateway.update(
                descriptor=descriptor,
                object_id=template.template_id.uuid,
                patch=payload,
            )
        return message_template_entity(tenant_id=tenant_id, row=row)

    async def load_template_version(
        self,
        *,
        tenant_id: EntityIdVO,
        template_version_id: TemplateVersionIdVO,
    ) -> TemplateVersionEntity | None:
        """Загружает template version entity из runtime-таблицы tenant."""
        descriptor = await self._resolve_descriptor(tenant_id, _TEMPLATE_VERSION)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=template_version_id.uuid,
        )
        if row is None:
            return None
        return template_version_entity(row)

    async def list_template_versions(
        self,
        *,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
    ) -> list[TemplateVersionEntity]:
        """Возвращает все версии template entity."""
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
            ),
            sorting=(SortSpec("version", "asc"),),
        )
        return [template_version_entity(row) for row in rows]

    async def save_template_version(
        self,
        *,
        tenant_id: EntityIdVO,
        version: TemplateVersionEntity,
    ) -> TemplateVersionEntity:
        """Создает или обновляет runtime-строку версии шаблона."""
        descriptor = await self._resolve_descriptor(tenant_id, _TEMPLATE_VERSION)
        existing = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=version.template_version_id.uuid,
        )
        payload = {
            "template_id": version.template_id.uuid,
            "version": version.version.value,
            "template_payload": version.template_payload,
            "variables_schema": version.variables_schema,
            "status": version.status.value,
            "activated_at": version.activated_at,
        }
        if existing is None:
            row = await self._runtime_command_gateway.insert(
                descriptor=descriptor,
                payload={
                    "id": version.template_version_id.uuid,
                    **payload,
                },
            )
        else:
            row = await self._runtime_command_gateway.update(
                descriptor=descriptor,
                object_id=version.template_version_id.uuid,
                patch=payload,
            )
        return template_version_entity(row)

    async def save_template_versions(
        self,
        *,
        tenant_id: EntityIdVO,
        versions: list[TemplateVersionEntity],
    ) -> list[TemplateVersionEntity]:
        """Сохраняет несколько версий шаблона."""
        saved = []
        for version in versions:
            saved.append(
                await self.save_template_version(
                    tenant_id=tenant_id,
                    version=version,
                )
            )
        return saved

    async def load_provider_connector(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connector_id: ProviderConnectorIdVO,
    ) -> ProviderConnector | None:
        """Загружает provider connector entity для domain invariant checks."""
        descriptor = await self._resolve_descriptor(tenant_id, _CONNECTOR)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=provider_connector_id.uuid,
        )
        if row is None:
            return None
        return provider_connector_entity(row)

    async def load_provider_message_type(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_message_type_id: ProviderMessageTypeIdVO,
    ) -> ProviderMessageType | None:
        """Загружает provider message type entity для domain invariant checks."""
        descriptor = await self._resolve_descriptor(tenant_id, _MESSAGE_TYPE)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=provider_message_type_id.uuid,
        )
        if row is None:
            return None
        return provider_message_type_entity(row)

    async def _resolve_descriptor(self, tenant_id: EntityIdVO, object_name: str):
        """Получает runtime descriptor communication-объекта для tenant."""
        return await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=object_name,
        )


__all__ = ["MessageTemplateRuntimeRepository"]
