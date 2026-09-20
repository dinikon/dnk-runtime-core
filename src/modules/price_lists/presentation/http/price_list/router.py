from fastapi import APIRouter

router = APIRouter()
from src.modules.price_lists.presentation.http.price_list.controller.preview_schedule import (
    router as preview_schedule_router,
)

router.include_router(preview_schedule_router, prefix="/price-lists")
from src.modules.price_lists.presentation.http.price_list.controller.activate_price_list import (
    router as activate_price_list_router,
)

router.include_router(activate_price_list_router, prefix="/price-lists")
from src.modules.price_lists.presentation.http.price_list.controller.archive_price_list import (
    router as archive_price_list_router,
)

router.include_router(archive_price_list_router, prefix="/price-lists")
from src.modules.price_lists.presentation.http.price_list.controller.create_price_list import (
    router as create_price_list_router,
)

router.include_router(create_price_list_router, prefix="/price-lists")
from src.modules.price_lists.presentation.http.price_list.controller.delete_price_list import (
    router as delete_price_list_router,
)

router.include_router(delete_price_list_router, prefix="/price-lists")
from src.modules.price_lists.presentation.http.price_list.controller.list_price_lists import (
    router as list_price_lists_router,
)

router.include_router(list_price_lists_router, prefix="/price-lists")
from src.modules.price_lists.presentation.http.price_list.controller.pause_price_list import (
    router as pause_price_list_router,
)

router.include_router(pause_price_list_router, prefix="/price-lists")
from src.modules.price_lists.presentation.http.price_list.controller.preview_price_list import (
    router as preview_price_list_router,
)

router.include_router(preview_price_list_router, prefix="/price-lists")
from src.modules.price_lists.presentation.http.price_list.controller.restore_price_list import (
    router as restore_price_list_router,
)

router.include_router(restore_price_list_router, prefix="/price-lists")
from src.modules.price_lists.presentation.http.price_list.controller.resume_price_list import (
    router as resume_price_list_router,
)

router.include_router(resume_price_list_router, prefix="/price-lists")
from src.modules.price_lists.presentation.http.price_list.controller.save_mapping import (
    router as save_mapping_router,
)

router.include_router(save_mapping_router, prefix="/price-lists")
from src.modules.price_lists.presentation.http.price_list.controller.save_schedule import (
    router as save_schedule_router,
)

router.include_router(save_schedule_router, prefix="/price-lists")
from src.modules.price_lists.presentation.http.price_list.controller.sync_price_list import (
    router as sync_price_list_router,
)

router.include_router(sync_price_list_router, prefix="/price-lists")
from src.modules.price_lists.presentation.http.price_list.controller.update_settings import (
    router as update_settings_router,
)

router.include_router(update_settings_router, prefix="/price-lists")
from src.modules.price_lists.presentation.http.price_list.controller.get_price_list import (
    router as get_price_list_router,
)

router.include_router(get_price_list_router, prefix="/price-lists")

__all__ = ["router"]
