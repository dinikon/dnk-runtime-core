from fastapi import APIRouter, Depends

from src.modules.contact_points.presentation.http.controller.create_label import (
    create_label,
)
from src.modules.contact_points.presentation.http.controller.list_labels import (
    list_labels,
)
from src.modules.contact_points.presentation.http.controller.update_label import (
    update_label,
)
from src.modules.contact_points.presentation.http.response.create_label import (
    CreateLabelResponse,
)
from src.modules.contact_points.presentation.http.response.list_labels import (
    ListLabelResponse,
)
from src.modules.contact_points.presentation.http.response.update_label import (
    UpdateLabelResponse,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf

router = APIRouter(prefix="/contact-points/labels", tags=["contact-point-labels"])
router.add_api_route(
    "", list_labels, methods=["GET"], response_model=list[ListLabelResponse]
)
router.add_api_route(
    "",
    create_label,
    methods=["POST"],
    status_code=201,
    response_model=CreateLabelResponse,
    dependencies=[Depends(require_csrf)],
)
router.add_api_route(
    "/{label_id}",
    update_label,
    methods=["PATCH"],
    response_model=UpdateLabelResponse,
    dependencies=[Depends(require_csrf)],
)
