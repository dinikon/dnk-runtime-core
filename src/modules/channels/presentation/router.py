from src.modules.channels.presentation.stock_sync.router import router as stock_router

"""Объединяет HTTP-маршруты агрегатов Channels."""

from fastapi import APIRouter, Depends
from src.modules.channels.presentation.http.transaction import prepare_channels_read
from src.modules.channels.presentation.channel.router import router as channel_router
from src.modules.channels.presentation.sync_run.router import router as sync_run_router
from src.modules.channels.presentation.external_publication.router import (
    router as publication_router,
)
from src.modules.channels.presentation.catalog_binding.router import (
    router as binding_router,
)

router = APIRouter(dependencies=[Depends(prepare_channels_read)])
router.include_router(binding_router)
router.include_router(channel_router)
router.include_router(sync_run_router)
router.include_router(publication_router)

router.include_router(stock_router)
