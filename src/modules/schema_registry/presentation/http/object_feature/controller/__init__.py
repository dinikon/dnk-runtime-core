from src.modules.schema_registry.presentation.http.object_feature.controller.disable_object_feature_controller import (
    router as disable_object_feature_router,
)
from src.modules.schema_registry.presentation.http.object_feature.controller.enable_object_feature_controller import (
    router as enable_object_feature_router,
)
from src.modules.schema_registry.presentation.http.object_feature.controller.get_object_feature_config_controller import (
    router as get_object_feature_config_router,
)
from src.modules.schema_registry.presentation.http.object_feature.controller.list_object_features_controller import (
    router as list_object_features_router,
)
from src.modules.schema_registry.presentation.http.object_feature.controller.update_object_feature_config_controller import (
    router as update_object_feature_config_router,
)

__all__ = [
    "disable_object_feature_router",
    "enable_object_feature_router",
    "get_object_feature_config_router",
    "list_object_features_router",
    "update_object_feature_config_router",
]
