from __future__ import annotations

from src.modules.communication.application.services import JsonSchemaValidationService
from src.modules.communication.application.template.command import (
    ActivateTemplateVersionCommand,
    CreateMessageTemplateCommand,
    CreateTemplateVersionCommand,
)
from src.modules.communication.application.template.dto import (
    MessageTemplateDTO,
    TemplateVersionDTO,
)
from src.modules.communication.application.template.ports import (
    MessageTemplateRepositoryProtocol,
)
from src.modules.communication.domain.error import (
    CommunicationValidationError,
)
from src.modules.communication.domain.message_template import (
    MessageTemplateNotFoundError,
    TemplateVersionNotFoundError,
)
from src.modules.communication.domain.provider_connector import (
    ProviderConnectorNotFoundError,
    ProviderMessageTypeNotFoundError,
)
from src.modules.shared.kernel.time.ports import ClockPort


class CreateMessageTemplateUseCase:
    """Creates provider-bound message templates."""

    def __init__(self, repository: MessageTemplateRepositoryProtocol) -> None:
        self._repository = repository

    async def __call__(
        self,
        command: CreateMessageTemplateCommand,
    ) -> MessageTemplateDTO:
        connector = await self._repository.get_connector(
            command.tenant_id,
            command.provider_connector_id,
        )
        if connector is None:
            raise ProviderConnectorNotFoundError()
        message_type = await self._repository.get_message_type(
            command.tenant_id,
            command.provider_message_type_id,
        )
        if message_type is None:
            raise ProviderMessageTypeNotFoundError()
        if message_type.provider_connector_id.uuid != command.provider_connector_id:
            raise CommunicationValidationError(
                "Provider message type does not belong to provider connector."
            )
        if message_type.channel_code != command.channel_code:
            raise CommunicationValidationError(
                "Template channel must match provider message type channel."
            )
        template = await self._repository.create_template(
            tenant_id=command.tenant_id,
            template_code=command.template_code,
            name=command.name,
            description=command.description,
            provider_connector_id=command.provider_connector_id,
            provider_message_type_id=command.provider_message_type_id,
            channel_code=command.channel_code,
            message_class=command.message_class,
        )
        return MessageTemplateDTO(
            template_id=template.template_id.uuid,
            tenant_id=template.tenant_id.uuid,
            template_code=template.template_code,
            name=template.name,
            description=template.description,
            provider_connector_id=template.provider_connector_id.uuid,
            provider_message_type_id=template.provider_message_type_id.uuid,
            channel_code=template.channel_code,
            message_class=template.message_class,
            status=template.status,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )


class CreateTemplateVersionUseCase:
    """Creates a new validated template version."""

    def __init__(
        self,
        repository: MessageTemplateRepositoryProtocol,
        schema_validator: JsonSchemaValidationService,
    ) -> None:
        self._repository = repository
        self._schema_validator = schema_validator

    async def __call__(
        self,
        command: CreateTemplateVersionCommand,
    ) -> TemplateVersionDTO:
        template = await self._repository.get_template(
            tenant_id=command.tenant_id,
            template_id=command.template_id,
        )
        if template is None:
            raise MessageTemplateNotFoundError()
        message_type = await self._repository.get_message_type(
            command.tenant_id,
            template.provider_message_type_id.uuid,
        )
        if message_type is None:
            raise ProviderMessageTypeNotFoundError()
        self._schema_validator.validate(
            command.template_payload,
            message_type.field_schema,
            "template_payload",
        )
        self._schema_validator.check_schema(
            command.variables_schema,
            "variables_schema",
        )
        version = await self._repository.create_template_version(
            tenant_id=command.tenant_id,
            template_id=template.template_id.uuid,
            template_payload=command.template_payload,
            variables_schema=command.variables_schema,
        )
        return TemplateVersionDTO(
            template_version_id=version.template_version_id.uuid,
            template_id=version.template_id.uuid,
            version_no=version.version_no,
            template_payload=dict(version.template_payload or {}),
            variables_schema=dict(version.variables_schema or {}),
            status=version.status,
            created_at=version.created_at,
            activated_at=version.activated_at,
        )


class ActivateTemplateVersionUseCase:
    """Activates a template version and deprecates the previous active version."""

    def __init__(
        self,
        repository: MessageTemplateRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        self._repository = repository
        self._clock = clock

    async def __call__(
        self,
        command: ActivateTemplateVersionCommand,
    ) -> TemplateVersionDTO:
        template = await self._repository.get_template(
            tenant_id=command.tenant_id,
            template_id=command.template_id,
        )
        if template is None:
            raise MessageTemplateNotFoundError()
        version = await self._repository.get_template_version(
            command.tenant_id,
            command.template_version_id,
        )
        if version is None or version.template_id != template.template_id:
            raise TemplateVersionNotFoundError()
        activated = await self._repository.activate_template_version(
            tenant_id=command.tenant_id,
            template=template,
            version=version,
            now=self._clock.now(),
        )
        return TemplateVersionDTO(
            template_version_id=activated.template_version_id.uuid,
            template_id=activated.template_id.uuid,
            version_no=activated.version_no,
            template_payload=dict(activated.template_payload or {}),
            variables_schema=dict(activated.variables_schema or {}),
            status=activated.status,
            created_at=activated.created_at,
            activated_at=activated.activated_at,
        )


class ListMessageTemplatesUseCase:
    """Lists tenant templates with active version metadata."""

    def __init__(self, repository: MessageTemplateRepositoryProtocol) -> None:
        self._repository = repository

    async def __call__(self, tenant_id) -> list[MessageTemplateDTO]:
        templates = await self._repository.list_templates(tenant_id)
        result: list[MessageTemplateDTO] = []
        for template in templates:
            active_version = await self._repository.get_active_template_version(
                tenant_id,
                template.template_id.uuid,
            )
            result.append(
                MessageTemplateDTO(
                    template_id=template.template_id.uuid,
                    tenant_id=template.tenant_id.uuid,
                    template_code=template.template_code,
                    name=template.name,
                    description=template.description,
                    provider_connector_id=template.provider_connector_id.uuid,
                    provider_message_type_id=template.provider_message_type_id.uuid,
                    channel_code=template.channel_code,
                    message_class=template.message_class,
                    status=template.status,
                    created_at=template.created_at,
                    updated_at=template.updated_at,
                    active_version_id=(
                        active_version.template_version_id.uuid
                        if active_version is not None
                        else None
                    ),
                    active_version_no=(
                        active_version.version_no
                        if active_version is not None
                        else None
                    ),
                )
            )
        return result


__all__ = [
    "ActivateTemplateVersionUseCase",
    "CreateMessageTemplateUseCase",
    "CreateTemplateVersionUseCase",
    "ListMessageTemplatesUseCase",
]
