from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from src.modules.communication.application.template.dto import MessageTemplateDTO
from src.modules.communication.application.template.query import (
    MessageTemplateQueryRepositoryProtocol,
)
from src.modules.communication.domain.message_template import (
    ChannelCodeVO,
    MessageClassVO,
    MessageTemplateCodeVO,
    MessageTemplateRepositoryProtocol,
    MessageTemplateEntity,
    MessageTemplateIdVO,
    MessageTemplateNameVO,
    MessageTemplateProviderLookupProtocol,
    TemplateStatusVO,
    TemplateVersionEntity,
    TemplateVersionIdVO,
    TemplateVersionStatusVO,
    TemplateVersionTimestampVO,
)
from src.modules.communication.domain.provider_connector import (
    ProviderConnector,
    ProviderConnectorIdVO,
    ProviderMessageType,
    ProviderMessageTypeIdVO,
)
from src.modules.runtime_data import FilterSpec, PageSpec, SortSpec
from src.modules.runtime_data.application.ports import (
    RuntimeCommandGateway,
    RuntimeQueryGateway,
)
from src.modules.schema_registry.runtime import RuntimeObjectResolverProtocol
from src.modules.shared import EntityIdVO


class MessageTemplateRuntimeRepository(
    MessageTemplateRepositoryProtocol,
    MessageTemplateProviderLookupProtocol,
    MessageTemplateQueryRepositoryProtocol,
):
    """Runtime repository message template aggregate."""

    _CONNECTOR = "communication_provider_connector"
    _MESSAGE_TYPE = "communication_provider_message_type"
    _TEMPLATE = "communication_message_template"
    _TEMPLATE_VERSION = "communication_template_version"

    def __init__(
        self,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        runtime_command_gateway: RuntimeCommandGateway,
        runtime_query_gateway: RuntimeQueryGateway,
    ) -> None:
        """Инициализирует repository resolver-ом descriptor и runtime gateways."""
        self._runtime_object_resolver = runtime_object_resolver
        self._runtime_command_gateway = runtime_command_gateway
        self._runtime_query_gateway = runtime_query_gateway

    async def load_template(
        self,
        *,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
    ) -> MessageTemplateEntity | None:
        """Загружает message template entity из runtime-таблицы tenant."""
        descriptor = await self._resolve_descriptor(tenant_id, self._TEMPLATE)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=template_id.uuid,
        )
        if row is None:
            return None
        return self._template_entity(tenant_id, row)

    async def load_template_by_code(
        self,
        *,
        tenant_id: EntityIdVO,
        template_code: MessageTemplateCodeVO,
    ) -> MessageTemplateEntity | None:
        """Загружает message template entity по tenant-local code."""
        descriptor = await self._resolve_descriptor(tenant_id, self._TEMPLATE)
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            filters=(FilterSpec("template_code", "eq", template_code.value),),
            page=PageSpec(limit=1, offset=0),
        )
        if not rows:
            return None
        return self._template_entity(tenant_id, rows[0])

    async def save_template(
        self,
        *,
        tenant_id: EntityIdVO,
        template: MessageTemplateEntity,
    ) -> MessageTemplateEntity:
        """Создает или обновляет runtime-строку шаблона и возвращает entity."""
        descriptor = await self._resolve_descriptor(tenant_id, self._TEMPLATE)
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
        return self._template_entity(tenant_id, row)

    async def load_template_version(
        self,
        *,
        tenant_id: EntityIdVO,
        template_version_id: TemplateVersionIdVO,
    ) -> TemplateVersionEntity | None:
        """Загружает template version entity из runtime-таблицы tenant."""
        descriptor = await self._resolve_descriptor(tenant_id, self._TEMPLATE_VERSION)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=template_version_id.uuid,
        )
        if row is None:
            return None
        return self._template_version_entity(row)

    async def list_template_versions(
        self,
        *,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
    ) -> list[TemplateVersionEntity]:
        """Возвращает все версии template entity."""
        descriptor = await self._resolve_descriptor(tenant_id, self._TEMPLATE_VERSION)
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            filters=(FilterSpec("template_id", "eq", template_id.uuid),),
            sorting=(SortSpec("version", "asc"),),
        )
        return [self._template_version_entity(row) for row in rows]

    async def save_template_version(
        self,
        *,
        tenant_id: EntityIdVO,
        version: TemplateVersionEntity,
    ) -> TemplateVersionEntity:
        """Создает или обновляет runtime-строку версии шаблона."""
        descriptor = await self._resolve_descriptor(tenant_id, self._TEMPLATE_VERSION)
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
        return self._template_version_entity(row)

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
        """Загружает provider connector entity."""
        descriptor = await self._resolve_descriptor(tenant_id, self._CONNECTOR)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=provider_connector_id.uuid,
        )
        if row is None:
            return None
        return self._provider_connector_entity(row)

    async def load_provider_message_type(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_message_type_id: ProviderMessageTypeIdVO,
    ) -> ProviderMessageType | None:
        """Загружает provider message type entity."""
        descriptor = await self._resolve_descriptor(tenant_id, self._MESSAGE_TYPE)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=provider_message_type_id.uuid,
        )
        if row is None:
            return None
        return self._provider_message_type_entity(row)

    async def list_templates(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> list[MessageTemplateDTO]:
        """Возвращает список MessageTemplateDTO с active version metadata."""
        descriptor = await self._resolve_descriptor(tenant_id, self._TEMPLATE)
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            sorting=(SortSpec("template_code"),),
        )
        result = []
        for row in rows:
            active_version = await self._load_active_template_version_row(
                tenant_id=tenant_id,
                template_id=MessageTemplateIdVO.from_value(
                    self._as_uuid(row.get("id"))
                ),
            )
            result.append(self._template_dto(tenant_id, row, active_version))
        return result

    async def _load_active_template_version_row(
        self,
        *,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
    ) -> Mapping[str, Any] | None:
        """Загружает runtime row активной версии шаблона."""
        descriptor = await self._resolve_descriptor(tenant_id, self._TEMPLATE_VERSION)
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            filters=(
                FilterSpec("template_id", "eq", template_id.uuid),
                FilterSpec("status", "eq", TemplateVersionStatusVO.ACTIVE.value),
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

    @classmethod
    def _template_entity(
        cls,
        tenant_id: EntityIdVO,
        row: Mapping[str, Any],
    ) -> MessageTemplateEntity:
        """Мапит runtime row в MessageTemplateEntity."""
        return MessageTemplateEntity(
            template_id=MessageTemplateIdVO.from_value(cls._as_uuid(row.get("id"))),
            created_at=cls._as_datetime(row.get("created_at")),
            updated_at=cls._as_datetime(row.get("updated_at")),
            tenant_id=tenant_id,
            template_code=MessageTemplateCodeVO(cls._as_str(row.get("template_code"))),
            name=MessageTemplateNameVO(cls._as_str(row.get("name"))),
            description=cls._as_optional_str(row.get("description")),
            provider_connector_id=ProviderConnectorIdVO.from_value(
                cls._as_uuid(row.get("provider_connector_id"))
            ),
            provider_message_type_id=ProviderMessageTypeIdVO.from_value(
                cls._as_uuid(row.get("provider_message_type_id"))
            ),
            channel_code=ChannelCodeVO(cls._as_str(row.get("channel_code"))),
            message_class=MessageClassVO(cls._as_str(row.get("message_class"))),
            status=TemplateStatusVO(cls._as_str(row.get("status"))),
        )

    @classmethod
    def _template_version_entity(
        cls,
        row: Mapping[str, Any],
    ) -> TemplateVersionEntity:
        """Мапит runtime row в TemplateVersionEntity."""
        version = row.get("version") or row.get("created_at")
        return TemplateVersionEntity(
            template_version_id=TemplateVersionIdVO.from_value(
                cls._as_uuid(row.get("id"))
            ),
            created_at=cls._as_datetime(row.get("created_at")),
            activated_at=cls._as_optional_datetime(row.get("activated_at")),
            template_id=MessageTemplateIdVO.from_value(
                cls._as_uuid(row.get("template_id"))
            ),
            version=TemplateVersionTimestampVO(cls._as_datetime(version)),
            template_payload=cls._as_dict(row.get("template_payload")),
            variables_schema=cls._as_dict(row.get("variables_schema")),
            status=TemplateVersionStatusVO(cls._as_str(row.get("status"))),
        )

    @classmethod
    def _template_dto(
        cls,
        tenant_id: EntityIdVO,
        row: Mapping[str, Any],
        active_version: Mapping[str, Any] | None,
    ) -> MessageTemplateDTO:
        """Мапит runtime row в MessageTemplateDTO."""
        return MessageTemplateDTO(
            template_id=cls._as_uuid(row.get("id")),
            tenant_id=tenant_id.uuid,
            template_code=cls._as_str(row.get("template_code")),
            name=cls._as_str(row.get("name")),
            description=cls._as_optional_str(row.get("description")),
            provider_connector_id=cls._as_uuid(row.get("provider_connector_id")),
            provider_message_type_id=cls._as_uuid(row.get("provider_message_type_id")),
            channel_code=cls._as_str(row.get("channel_code")),
            message_class=cls._as_str(row.get("message_class")),
            status=cls._as_str(row.get("status")),
            created_at=cls._as_datetime(row.get("created_at")),
            updated_at=cls._as_datetime(row.get("updated_at")),
            active_version_id=(
                None
                if active_version is None
                else cls._as_uuid(active_version.get("id"))
            ),
            active_version=(
                None
                if active_version is None
                else TemplateVersionTimestampVO(
                    cls._as_datetime(active_version.get("version"))
                ).value
            ),
        )

    @classmethod
    def _provider_connector_entity(cls, row: Mapping[str, Any]) -> ProviderConnector:
        """Мапит runtime row в ProviderConnector."""
        return ProviderConnector(
            provider_connector_id=ProviderConnectorIdVO.from_value(
                cls._as_uuid(row.get("id"))
            ),
            provider_code=cls._as_str(row.get("provider_code")),
            provider_name=cls._as_str(row.get("provider_name")),
            version=cls._as_str(row.get("version")),
            connector_type=cls._as_str(row.get("connector_type")),
            yaml_spec=cls._as_dict(row.get("yaml_spec")),
            yaml_checksum=cls._as_str(row.get("yaml_checksum")),
            status=cls._as_str(row.get("status")),
            created_at=cls._as_datetime(row.get("created_at")),
            updated_at=cls._as_datetime(row.get("updated_at")),
        )

    @classmethod
    def _provider_message_type_entity(
        cls,
        row: Mapping[str, Any],
    ) -> ProviderMessageType:
        """Мапит runtime row в ProviderMessageType."""
        return ProviderMessageType(
            provider_message_type_id=ProviderMessageTypeIdVO.from_value(
                cls._as_uuid(row.get("id"))
            ),
            provider_connector_id=ProviderConnectorIdVO.from_value(
                cls._as_uuid(row.get("provider_connector_id"))
            ),
            message_type_code=cls._as_str(row.get("message_type_code")),
            channel_code=cls._as_str(row.get("channel_code")),
            name=cls._as_str(row.get("name")),
            field_schema=cls._as_dict(row.get("field_schema")),
            ui_schema=cls._as_dict(row.get("ui_schema")),
            is_active=bool(row.get("is_active")),
        )

    @staticmethod
    def _as_uuid(value: Any) -> UUID:
        """Достает UUID из runtime row."""
        if isinstance(value, UUID):
            return value
        if isinstance(value, str):
            return UUID(value)
        raise TypeError("Runtime row must contain UUID value.")

    @staticmethod
    def _as_datetime(value: Any) -> datetime:
        """Достает datetime из runtime row."""
        if isinstance(value, datetime):
            return value
        raise TypeError("Runtime row must contain datetime value.")

    @staticmethod
    def _as_optional_datetime(value: Any) -> datetime | None:
        """Достает optional datetime из runtime row."""
        if value is None:
            return None
        return MessageTemplateRuntimeRepository._as_datetime(value)

    @staticmethod
    def _as_str(value: Any) -> str:
        """Достает строку из runtime row."""
        if isinstance(value, str):
            return value
        raise TypeError("Runtime row must contain string value.")

    @staticmethod
    def _as_optional_str(value: Any) -> str | None:
        """Достает optional строку из runtime row."""
        if value is None:
            return None
        return MessageTemplateRuntimeRepository._as_str(value)

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        """Достает dict из runtime row."""
        if isinstance(value, dict):
            return dict(value)
        raise TypeError("Runtime row must contain dict value.")


__all__ = ["MessageTemplateRuntimeRepository"]
