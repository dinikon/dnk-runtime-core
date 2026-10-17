from fastapi import APIRouter
from src.modules.channels.presentation.channel.router import router as channel_router
from src.modules.channels.presentation.external_publication.router import (
    router as publication_router,
)
from src.modules.channels.presentation.publication_import_run.router import (
    router as import_router,
)

router = APIRouter()
router.include_router(channel_router)
router.include_router(publication_router)
router.include_router(import_router)
