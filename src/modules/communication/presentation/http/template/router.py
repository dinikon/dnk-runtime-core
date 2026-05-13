from src.modules.communication.presentation.http.template import router
from src.modules.communication.presentation.http.template.controller import (
    activate_template_version,
    create_message_template,
    create_template_version,
    list_message_templates,
)
from src.modules.communication.presentation.http.template.requests import (
    CreateMessageTemplateRequestSchema,
    CreateTemplateVersionRequestSchema,
)
from src.modules.communication.presentation.http.template.responses import (
    ListMessageTemplatesResponseSchema,
    MessageTemplateResponseSchema,
    TemplateVersionResponseSchema,
)

__all__ = [
    "CreateMessageTemplateRequestSchema",
    "CreateTemplateVersionRequestSchema",
    "ListMessageTemplatesResponseSchema",
    "MessageTemplateResponseSchema",
    "TemplateVersionResponseSchema",
    "activate_template_version",
    "create_message_template",
    "create_template_version",
    "list_message_templates",
    "router",
]
