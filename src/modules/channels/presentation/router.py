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

from src.modules.channels.presentation.product_representation.router import (
    router as representation_router,
)

router.include_router(representation_router)

from src.modules.channels.presentation.publication_import.router import (
    router as import_router,
)

router.include_router(import_router)

from src.modules.channels.presentation.content_update.router import (
    router as content_update_router,
)

router.include_router(content_update_router)

from src.modules.channels.presentation.batch_export.router import (
    router as batch_export_router,
)

router.include_router(batch_export_router)
