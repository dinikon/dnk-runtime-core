from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from src.modules.communication.domain.message_template.entity import (
    MessageTemplate,
    TemplateVersion,
)
from src.modules.communication.domain.message_template.error import (
    MessageTemplateNotFoundError,
    TemplateVersionNotFoundError,
)
from src.modules.communication.domain.message_template.repository import (
    MessageTemplateProviderLookupProtocol,
    MessageTemplateRepositoryProtocol,
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
from src.modules.shared.kernel.time.ports import ClockPort


class MessageTemplateSchemaValidatorProtocol(Protocol):
    """Port for validating template payloads and variables schemas."""

    def validate_template_payload(
        self,
        payload: dict[str, Any],
        field_schema: dict[str, Any],
    ) -> None:
        """Validates a template payload against provider message type schema."""
        ...

    def validate_variables_schema(self, schema: dict[str, Any]) -> None:
        """Validates template variables schema."""
        ...


class MessageTemplateService:
    """Domain service for message template aggregate workflows."""

    def __init__(
        self,
        *,
        repository: MessageTemplateRepositoryProtocol,
        provider_lookup: MessageTemplateProviderLookupProtocol,
        schema_validator: MessageTemplateSchemaValidatorProtocol,
        clock: ClockPort,
        template_id_provider: Callable[[], MessageTemplateIdVO],
        template_version_id_provider: Callable[[], TemplateVersionIdVO],
    ) -> None:
        self._repository = repository
        self._provider_lookup = provider_lookup
        self._schema_validator = schema_validator
        self._clock = clock
        self._template_id_provider = template_id_provider
        self._template_version_id_provider = template_version_id_provider

    async def create_template(
        self,
        *,
        tenant_id: EntityIdVO,
        template_code: str,
        name: str,
        description: str | None,
        provider_connector_id: ProviderConnectorIdVO,
        provider_message_type_id: ProviderMessageTypeIdVO,
        channel_code: str,
        message_class: str,
    ) -> MessageTemplate:
        """Creates a draft provider-bound message template."""
        connector = await self._provider_lookup.load_provider_connector(
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
        )
        if connector is None:
            raise ProviderConnectorNotFoundError()

        message_type = await self._provider_lookup.load_provider_message_type(
            tenant_id=tenant_id,
            provider_message_type_id=provider_message_type_id,
        )
        if message_type is None:
            raise ProviderMessageTypeNotFoundError()

        template = MessageTemplate.create(
            template_id=self._template_id_provider(),
            tenant_id=tenant_id,
            template_code=template_code,
            name=name,
            description=description,
            provider_connector_id=provider_connector_id,
            provider_message_type_id=provider_message_type_id,
            channel_code=channel_code,
            message_class=message_class,
            now=self._clock.now(),
        )
        template.ensure_message_type_binding(message_type)
        return await self._repository.save_template(
            tenant_id=tenant_id,
            template=template,
        )

    async def create_template_version(
        self,
        *,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
        template_payload: dict[str, Any],
        variables_schema: dict[str, Any],
    ) -> TemplateVersion:
        """Creates a validated draft template version."""
        template = await self._repository.load_template(
            tenant_id=tenant_id,
            template_id=template_id,
        )
        if template is None:
            raise MessageTemplateNotFoundError()

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
        version = TemplateVersion.create(
            template_version_id=self._template_version_id_provider(),
            template_id=template.template_id,
            version=now,
            template_payload=template_payload,
            variables_schema=variables_schema,
            now=now,
        )
        return await self._repository.save_template_version(
            tenant_id=tenant_id,
            version=version,
        )

    async def activate_template_version(
        self,
        *,
        tenant_id: EntityIdVO,
        template_id: MessageTemplateIdVO,
        template_version_id: TemplateVersionIdVO,
    ) -> TemplateVersion:
        """Activates a template version and deprecates previous active versions."""
        template = await self._repository.load_template(
            tenant_id=tenant_id,
            template_id=template_id,
        )
        if template is None:
            raise MessageTemplateNotFoundError()

        selected = await self._repository.load_template_version(
            tenant_id=tenant_id,
            template_version_id=template_version_id,
        )
        if selected is None:
            raise TemplateVersionNotFoundError()
        selected.ensure_belongs_to(template)

        now = self._clock.now()
        versions_by_id = {
            version.template_version_id: version
            for version in await self._repository.list_template_versions(
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
        await self._repository.save_template(
            tenant_id=tenant_id,
            template=template,
        )
        saved_versions = await self._repository.save_template_versions(
            tenant_id=tenant_id,
            versions=list(versions_by_id.values()),
        )
        for version in saved_versions:
            if version.template_version_id == selected.template_version_id:
                return version
        return selected


__all__ = [
    "MessageTemplateSchemaValidatorProtocol",
    "MessageTemplateService",
]
