from src.modules.contact_point.presentation.http.controllers.attach_contact_point import (
    router as attach_contact_point_router,
)
from src.modules.contact_point.presentation.http.controllers.detach_contact_point import (
    router as detach_contact_point_router,
)
from src.modules.contact_point.presentation.http.controllers.get_contact_point import (
    router as get_contact_point_router,
)
from src.modules.contact_point.presentation.http.controllers.list_contact_point_bindings import (
    router as list_contact_point_bindings_router,
)
from src.modules.contact_point.presentation.http.controllers.list_contact_points import (
    router as list_contact_points_router,
)
from src.modules.contact_point.presentation.http.controllers.list_owner_contact_points import (
    router as list_owner_contact_points_router,
)

__all__ = [
    "attach_contact_point_router",
    "detach_contact_point_router",
    "get_contact_point_router",
    "list_contact_point_bindings_router",
    "list_contact_points_router",
    "list_owner_contact_points_router",
]
