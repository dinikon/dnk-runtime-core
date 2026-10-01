from fastapi import APIRouter, Depends
from src.modules.identity.presentation.http.csrf import require_csrf

from src.modules.identity.presentation.http.console_auth.controller.confirm_email_otp import (
    router as confirm_email_otp_router,
)
from src.modules.identity.presentation.http.console_auth.controller.get_current_user import (
    router as get_current_user_router,
)
from src.modules.identity.presentation.http.console_auth.controller.logout_current_session import (
    router as logout_current_session_router,
)
from src.modules.identity.presentation.http.console_auth.controller.request_email_otp import (
    router as request_email_otp_router,
)
from src.modules.identity.presentation.http.console_auth.controller.update_current_user_profile import (
    router as update_current_user_profile_router,
)

router = APIRouter(prefix="/auth", dependencies=[Depends(require_csrf)])
router.include_router(request_email_otp_router)
router.include_router(confirm_email_otp_router)
router.include_router(get_current_user_router)
router.include_router(update_current_user_profile_router)
router.include_router(logout_current_session_router)

__all__ = ["router"]
