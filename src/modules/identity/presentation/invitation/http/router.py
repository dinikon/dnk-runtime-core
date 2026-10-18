from fastapi import APIRouter
from src.modules.identity.presentation.invitation.http.controller.accept_invitation import (
    router as accept_invitation_router,
)
from src.modules.identity.presentation.invitation.http.controller.create_invitation import (
    router as create_invitation_router,
)
from src.modules.identity.presentation.invitation.http.controller.delete_invitation import (
    router as delete_invitation_router,
)
from src.modules.identity.presentation.invitation.http.controller.invitation_otp import (
    router as invitation_otp_router,
)
from src.modules.identity.presentation.invitation.http.controller.invitations import (
    router as invitations_router,
)

router = APIRouter()
router.include_router(invitations_router)
router.include_router(create_invitation_router)
router.include_router(delete_invitation_router)
router.include_router(invitation_otp_router)
router.include_router(accept_invitation_router)
