from dataclasses import dataclass, field
from typing import Any

from src.modules.communication.domain.message_template import (
    MessageTemplateIdVO,
    TemplateVersionIdVO,
)
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class CreateTemplateVersionCommand:
    """Команда application-слоя на создание версии шаблона."""

    tenant_id: EntityIdVO
    template_id: MessageTemplateIdVO
    template_version_id: TemplateVersionIdVO
    template_payload: dict[str, Any]
    variables_schema: dict[str, Any] = field(default_factory=dict)


__all__ = ["CreateTemplateVersionCommand"]
