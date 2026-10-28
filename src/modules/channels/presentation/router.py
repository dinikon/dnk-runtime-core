"""Объединяет HTTP-маршруты агрегатов Channels."""

from fastapi import APIRouter

from src.modules.channels.presentation.channel.router import router as channel_router
from src.modules.channels.presentation.sync_run.router import router as sync_run_router
from src.modules.channels.presentation.external_publication.router import (
    router as publication_router,
)

router = APIRouter()
router.include_router(channel_router)
router.include_router(sync_run_router)
router.include_router(publication_router)
