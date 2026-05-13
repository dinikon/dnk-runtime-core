from dataclasses import dataclass

from src.modules.communication.domain.message_template import (
    MessageTemplateIdVO,
    TemplateVersionIdVO,
)
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class ActivateTemplateVersionCommand:
    """Команда application-слоя на активацию версии шаблона."""

    tenant_id: EntityIdVO
    template_id: MessageTemplateIdVO
    template_version_id: TemplateVersionIdVO


__all__ = ["ActivateTemplateVersionCommand"]
