from fastapi import APIRouter

from src.modules.custom_object.presentation.http.field.controller import (
    create_custom_field_router,
    delete_custom_field_router,
)
from src.modules.custom_object.presentation.http.object.controller import (
    create_custom_object_router,
    delete_custom_object_router,
    describe_custom_object_router,
    list_custom_objects_router,
)
from src.modules.custom_object.presentation.http.record.controller import (
    create_custom_record_router,
    delete_custom_record_router,
    get_custom_record_router,
    list_custom_records_router,
    update_custom_record_router,
)

router = APIRouter()
router.include_router(list_custom_objects_router)
router.include_router(create_custom_object_router)
router.include_router(delete_custom_object_router)
router.include_router(describe_custom_object_router)
router.include_router(create_custom_field_router)
router.include_router(delete_custom_field_router)
router.include_router(create_custom_record_router)
router.include_router(get_custom_record_router)
router.include_router(list_custom_records_router)
router.include_router(update_custom_record_router)
router.include_router(delete_custom_record_router)

__all__ = ["router"]
