from src.modules.custom_object.presentation.http.object.controller.create_custom_object import (
    router as create_custom_object_router,
)
from src.modules.custom_object.presentation.http.object.controller.delete_custom_object import (
    router as delete_custom_object_router,
)
from src.modules.custom_object.presentation.http.object.controller.describe_custom_object import (
    router as describe_custom_object_router,
)
from src.modules.custom_object.presentation.http.object.controller.list_custom_objects import (
    router as list_custom_objects_router,
)

__all__ = [
    "create_custom_object_router",
    "delete_custom_object_router",
    "describe_custom_object_router",
    "list_custom_objects_router",
]
