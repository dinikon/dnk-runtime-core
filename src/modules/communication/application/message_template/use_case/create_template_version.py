from typing import Protocol

from src.modules.communication.application.message_template.command import (
    CreateTemplateVersionCommand,
)
from src.modules.communication.application.message_template.dto import (
    TemplateVersionDTO,
)
from src.modules.communication.domain.message_template import (
    MessageTemplateService,
    TemplateVersionEntity,
)


class CreateTemplateVersionUseCaseProtocol(Protocol):
    """Порт use case создания версии шаблона."""

    async def __call__(
        self, command: CreateTemplateVersionCommand
    ) -> TemplateVersionDTO:
        """Создает версию шаблона и возвращает DTO."""
        ...


class CreateTemplateVersionUseCase:
    """Use case создания версии шаблона через доменный сервис."""

    def __init__(self, service: MessageTemplateService) -> None:
        """Инициализирует use case доменным сервисом шаблонов."""
        self._service = service

    async def __call__(
        self,
        command: CreateTemplateVersionCommand,
    ) -> TemplateVersionDTO:
        """Выполняет команду создания версии и мапит entity в DTO."""
        version = await self._service.create_template_version(
            tenant_id=command.tenant_id,
            template_id=command.template_id,
            template_version_id=command.template_version_id,
            template_payload=command.template_payload,
            variables_schema=command.variables_schema,
        )
        return self._to_dto(version)

    @staticmethod
    def _to_dto(version: TemplateVersionEntity) -> TemplateVersionDTO:
        """Мапит TemplateVersionEntity в TemplateVersionDTO."""
        return TemplateVersionDTO(
            template_version_id=version.template_version_id.uuid,
            template_id=version.template_id.uuid,
            version=version.version.value,
            template_payload=dict(version.template_payload or {}),
            variables_schema=dict(version.variables_schema or {}),
            status=version.status.value,
            created_at=version.created_at,
            activated_at=version.activated_at,
        )


__all__ = [
    "CreateTemplateVersionUseCase",
    "CreateTemplateVersionUseCaseProtocol",
]
