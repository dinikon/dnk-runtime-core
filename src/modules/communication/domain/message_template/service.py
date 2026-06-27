from __future__ import annotations

from typing import Any, Protocol

from src.modules.communication.domain.message_template.entity import (
    MessageTemplateEntity,
    TemplateVersionEntity,
)
from src.modules.communication.domain.message_template.error import (
    MessageTemplateNotFoundError,
    TemplateVersionNotFoundError,
)
from src.modules.communication.domain.message_template.repository import (
    MessageTemplateRepositoryProtocol,
    MessageTemplateProviderLookupProtocol,
)
from src.modules.communication.domain.message_template.value_object import (
    MessageTemplateIdVO,
    TemplateVersionIdVO,
)
from src.modules.communication.domain.provider_connector.error import (
    ProviderConnectorNotFoundError,
    ProviderMessageTypeNotFoundError,
)
from src.modules.communication.domain.provider_connector.value_object import (
    ProviderConnectorIdVO,
    ProviderMessageTypeIdVO,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.time import ClockPort


class MessageTemplateSchemaValidatorProtocol(Protocol):
    """Порт валидации payload и variables schema шаблонов."""

    def validate_template_payload(
        self,
        payload: dict[str, Any],
        field_schema: dict[str, Any],
    ) -> None:
        """Проверяет payload шаблона по provider field schema."""
        ...

    def validate_variables_schema(self, schema: dict[str, Any]) -> None:
        """Проверяет JSON Schema переменных шаблона."""
        ...


class MessageTemplateService:
    """Доменный сервис сценариев message template aggregate."""

    def __init__(
        self,
        *,
        command_repository: MessageTemplateRepositoryProtocol,
        provider_lookup: MessageTemplateProviderLookupProtocol,
        schema_validator: MessageTemplateSchemaValidatorProtocol,
        clock: ClockPort,
    ) -> None:
        """Инициализирует сервис repository, provider lookup и clock-портом."""
        self._command_repository = command_repository
        self._provider_lookup = provider_lookup
        self._schema_validator = schema_validator
        self._clock = clock

    async def create_template(
        self,
        *,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
        name: str,
        description: str | None,
        provider_connector_id: ProviderConnectorIdVO,
        provider_message_type_id: ProviderMessageTypeIdVO,
        channel_code: str,
    ) -> MessageTemplateEntity:
        """Создает provider-bound шаблон сообщения и сохраняет его."""
        connector = await self._provider_lookup.load_provider_connector(
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
        )
        if connector is None:
            raise ProviderConnectorNotFoundError()
        connector.ensure_active()

        message_type = await self._provider_lookup.load_provider_message_type(
            tenant_id=tenant_id,
            provider_message_type_id=provider_message_type_id,
        )
        if message_type is None:
            raise ProviderMessageTypeNotFoundError()

        now = self._clock.now()
        template = MessageTemplateEntity.create(
            template_id=template_id,
            tenant_id=tenant_id,
            name=name,
            description=description,
            provider_connector_id=provider_connector_id,
            provider_message_type_id=provider_message_type_id,
            channel_code=channel_code,
            now=now,
        )
        template.ensure_message_type_binding(message_type)
        return await self._command_repository.save_template(
            tenant_id=tenant_id,
            template=template,
        )

    async def create_template_version(
        self,
        *,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
        template_version_id: TemplateVersionIdVO,
        template_payload: dict[str, Any],
        variables_schema: dict[str, Any],
    ) -> TemplateVersionEntity:
        """Создает валидированную черновую версию шаблона."""
        template = await self.get_template(
            tenant_id=tenant_id,
            template_id=template_id,
        )

        message_type = await self._provider_lookup.load_provider_message_type(
            tenant_id=tenant_id,
            provider_message_type_id=template.provider_message_type_id,
        )
        if message_type is None:
            raise ProviderMessageTypeNotFoundError()

        self._schema_validator.validate_template_payload(
            template_payload,
            message_type.field_schema,
        )
        self._schema_validator.validate_variables_schema(variables_schema)

        now = self._clock.now()
        version = TemplateVersionEntity.create(
            template_version_id=template_version_id,
            template_id=template.template_id,
            version=now,
            template_payload=template_payload,
            variables_schema=variables_schema,
            now=now,
        )
        return await self._command_repository.save_template_version(
            tenant_id=tenant_id,
            version=version,
        )

    async def activate_template_version(
        self,
        *,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
        template_version_id: TemplateVersionIdVO,
    ) -> TemplateVersionEntity:
        """Активирует версию шаблона и деактуализирует прежнюю active version."""
        template = await self.get_template(
            tenant_id=tenant_id,
            template_id=template_id,
        )
        selected = await self._command_repository.load_template_version(
            tenant_id=tenant_id,
            template_version_id=template_version_id,
        )
        if selected is None:
            raise TemplateVersionNotFoundError()
        selected.ensure_belongs_to(template)

        now = self._clock.now()
        versions_by_id = {
            version.template_version_id: version
            for version in await self._command_repository.list_template_versions(
                tenant_id=tenant_id,
                template_id=template.template_id,
            )
        }
        versions_by_id[selected.template_version_id] = selected

        for version in versions_by_id.values():
            if version.template_version_id == selected.template_version_id:
                version.activate(now=now)
            else:
                version.deprecate()

        template.mark_active(now=now)
        await self._command_repository.save_template(
            tenant_id=tenant_id,
            template=template,
        )
        saved_versions = await self._command_repository.save_template_versions(
            tenant_id=tenant_id,
            versions=list(versions_by_id.values()),
        )
        for version in saved_versions:
            if version.template_version_id == selected.template_version_id:
                return version
        return selected

    async def get_template(
        self,
        *,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
    ) -> MessageTemplateEntity:
        """Возвращает шаблон tenant или поднимает MessageTemplateNotFoundError."""
        template = await self._command_repository.load_template(
            tenant_id=tenant_id,
            template_id=template_id,
        )
        if template is None:
            raise MessageTemplateNotFoundError()
        return template


__all__ = [
    "MessageTemplateSchemaValidatorProtocol",
    "MessageTemplateService",
]
