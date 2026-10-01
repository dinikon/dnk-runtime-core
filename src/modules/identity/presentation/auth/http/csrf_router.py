from fastapi import APIRouter
from src.modules.identity.presentation.auth.http.controller.csrf import (
    router as csrf_router,
)

router = APIRouter()
router.include_router(csrf_router)
