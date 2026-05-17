from fastapi import APIRouter

from src.modules.schema_registry.presentation.http.config.field.controller import (
    create_custom_field_router,
    delete_custom_field_router,
)
from src.modules.schema_registry.presentation.http.config.object.controller import (
    create_custom_object_router,
    delete_custom_object_router,
    describe_custom_object_router,
    list_custom_objects_router,
)
from src.modules.schema_registry.presentation.http.config.relation.controller import (
    relation_router,
)
from src.modules.schema_registry.presentation.http.object_feature.router import (
    router as object_feature_router,
)

router = APIRouter()
router.include_router(list_custom_objects_router)
router.include_router(create_custom_object_router)
router.include_router(delete_custom_object_router)
router.include_router(describe_custom_object_router)
router.include_router(create_custom_field_router)
router.include_router(delete_custom_field_router)
router.include_router(relation_router)
router.include_router(object_feature_router)

__all__ = ["router"]
