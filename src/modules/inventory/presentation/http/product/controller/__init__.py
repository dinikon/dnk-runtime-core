from .create_product import router as create_product_router
from .delete_product import router as delete_product_router
from .describe_product_fields import router as describe_product_fields_router
from .get_product import router as get_product_router
from .list_products import router as list_products_router
from .update_product import router as update_product_router

__all__ = [
    "create_product_router",
    "delete_product_router",
    "describe_product_fields_router",
    "get_product_router",
    "list_products_router",
    "update_product_router",
]
