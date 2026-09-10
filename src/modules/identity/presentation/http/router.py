from fastapi import APIRouter

from src.modules.identity.presentation.http.console_auth.controller import (
    confirm_email_otp_router,
    get_current_user_router,
    logout_current_session_router,
    request_email_otp_router,
    update_current_user_profile_router,
)

router = APIRouter(prefix="/auth")
router.include_router(request_email_otp_router)
router.include_router(confirm_email_otp_router)
router.include_router(get_current_user_router)
router.include_router(update_current_user_profile_router)
router.include_router(logout_current_session_router)

__all__ = ["router"]
