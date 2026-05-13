from typing import Protocol

from src.modules.communication.application.template.command import (
    CreateMessageTemplateCommand,
)
from src.modules.communication.application.template.dto import MessageTemplateDTO
from src.modules.communication.domain.message_template import (
    MessageTemplateEntity,
    MessageTemplateService,
)


class CreateMessageTemplateUseCaseProtocol(Protocol):
    """Порт use case создания message template."""

    async def __call__(
        self, command: CreateMessageTemplateCommand
    ) -> MessageTemplateDTO:
        """Создает message template и возвращает DTO."""
        ...


class CreateMessageTemplateUseCase:
    """Use case создания message template через доменный сервис."""

    def __init__(self, service: MessageTemplateService) -> None:
        """Инициализирует use case доменным сервисом шаблонов."""
        self._service = service

    async def __call__(
        self,
        command: CreateMessageTemplateCommand,
    ) -> MessageTemplateDTO:
        """Выполняет команду создания шаблона и мапит entity в DTO."""
        template = await self._service.create_template(
            tenant_id=command.tenant_id,
            template_id=command.template_id,
            template_code=command.template_code,
            name=command.name,
            description=command.description,
            provider_connector_id=command.provider_connector_id,
            provider_message_type_id=command.provider_message_type_id,
            channel_code=command.channel_code,
            message_class=command.message_class,
        )
        return self._to_dto(template)

    @staticmethod
    def _to_dto(template: MessageTemplateEntity) -> MessageTemplateDTO:
        """Мапит MessageTemplateEntity в MessageTemplateDTO."""
        return MessageTemplateDTO(
            template_id=template.template_id.uuid,
            tenant_id=template.tenant_id.uuid,
            template_code=template.template_code.value,
            name=template.name.value,
            description=template.description,
            provider_connector_id=template.provider_connector_id.uuid,
            provider_message_type_id=template.provider_message_type_id.uuid,
            channel_code=template.channel_code.value,
            message_class=template.message_class.value,
            status=template.status.value,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )


__all__ = [
    "CreateMessageTemplateUseCase",
    "CreateMessageTemplateUseCaseProtocol",
]
