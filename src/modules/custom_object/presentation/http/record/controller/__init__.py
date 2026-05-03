from src.modules.custom_object.presentation.http.record.controller.create_custom_record import (
    router as create_custom_record_router,
)
from src.modules.custom_object.presentation.http.record.controller.delete_custom_record import (
    router as delete_custom_record_router,
)
from src.modules.custom_object.presentation.http.record.controller.get_custom_record import (
    router as get_custom_record_router,
)
from src.modules.custom_object.presentation.http.record.controller.list_custom_records import (
    router as list_custom_records_router,
)
from src.modules.custom_object.presentation.http.record.controller.update_custom_record import (
    router as update_custom_record_router,
)

__all__ = [
    "create_custom_record_router",
    "delete_custom_record_router",
    "get_custom_record_router",
    "list_custom_records_router",
    "update_custom_record_router",
]
