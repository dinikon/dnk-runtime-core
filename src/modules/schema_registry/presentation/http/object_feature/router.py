from fastapi import APIRouter

from src.modules.schema_registry.presentation.http.object_feature.controller import (
    disable_object_feature_router,
    enable_object_feature_router,
    get_object_feature_config_router,
    list_object_features_router,
    update_object_feature_config_router,
)

router = APIRouter()

router.include_router(enable_object_feature_router)
router.include_router(disable_object_feature_router)
router.include_router(update_object_feature_config_router)
router.include_router(get_object_feature_config_router)
router.include_router(list_object_features_router)

__all__ = ["router"]
