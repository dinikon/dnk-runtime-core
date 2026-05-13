from src.modules.communication.presentation.http.template.controller.activate_template_version import (
    activate_template_version,
    router as activate_template_version_router,
)
from src.modules.communication.presentation.http.template.controller.create_message_template import (
    create_message_template,
    router as create_message_template_router,
)
from src.modules.communication.presentation.http.template.controller.create_template_version import (
    create_template_version,
    router as create_template_version_router,
)
from src.modules.communication.presentation.http.template.controller.list_message_templates import (
    list_message_templates,
    router as list_message_templates_router,
)

__all__ = [
    "activate_template_version",
    "activate_template_version_router",
    "create_message_template",
    "create_message_template_router",
    "create_template_version",
    "create_template_version_router",
    "list_message_templates",
    "list_message_templates_router",
]
