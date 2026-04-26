from src.modules.custom_object.presentation.http.field.controller.create_custom_field import (
    router as create_custom_field_router,
)
from src.modules.custom_object.presentation.http.field.controller.delete_custom_field import (
    router as delete_custom_field_router,
)

__all__ = [
    "create_custom_field_router",
    "delete_custom_field_router",
]
