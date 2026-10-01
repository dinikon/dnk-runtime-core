from src.modules.identity.presentation.user.http.router import router as user_router
from fastapi import APIRouter, Depends
from src.modules.identity.presentation.auth.http.controller.confirm_email_otp import (
    router as confirm_email_otp_router,
)
from src.modules.identity.presentation.auth.http.controller.logout_current_session import (
    router as logout_current_session_router,
)
from src.modules.identity.presentation.auth.http.controller.request_email_otp import (
    router as request_email_otp_router,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf

router = APIRouter(prefix="/auth", dependencies=[Depends(require_csrf)])
router.include_router(request_email_otp_router)
router.include_router(confirm_email_otp_router)
router.include_router(user_router)
router.include_router(logout_current_session_router)
