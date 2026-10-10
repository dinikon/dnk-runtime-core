from fastapi import APIRouter
from src.modules.files.presentation.storage_provider.router import (
    router as providers_router,
)
from src.modules.files.presentation.bucket.router import router as buckets_router

router = APIRouter()
router.include_router(providers_router)
router.include_router(buckets_router)
