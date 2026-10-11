from fastapi import APIRouter, Depends
from src.modules.identity.presentation.user.http.controller.get_current_user import (
    get_current_user,
)
from src.modules.identity.presentation.user.http.controller.update_current_user_profile import (
    update_current_user_profile,
)
from src.modules.identity.presentation.user.http.response.get_current_user import (
    GetCurrentUserResponseSchema,
)
from src.modules.identity.presentation.user.http.response.update_current_user_profile import (
    UpdateCurrentUserProfileResponseSchema,
)
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf

router = APIRouter(tags=["console-auth"])
router.add_api_route(
    "/me",
    get_current_user,
    methods=["GET"],
    response_model=GetCurrentUserResponseSchema,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/me",
    update_current_user_profile,
    methods=["PATCH"],
    response_model=UpdateCurrentUserProfileResponseSchema,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
