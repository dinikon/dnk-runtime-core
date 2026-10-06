"""Регистрация статических tenant-моделей и их исторических имён."""

import src.modules.crm.infrastructure.persistence.models.company  # noqa: F401
import src.modules.crm.infrastructure.persistence.models.contact  # noqa: F401
import src.modules.crm.infrastructure.persistence.models.contact_company  # noqa: F401
import src.modules.contact_points.infrastructure.persistence.models.contact_point  # noqa: F401
import src.modules.contact_points.infrastructure.persistence.models.contact_point_binding  # noqa: F401
import src.modules.contact_points.infrastructure.persistence.models.contact_point_label  # noqa: F401
import src.modules.inventory.infrastructure.persistence.models.warehouse  # noqa: F401
import src.modules.inventory.infrastructure.persistence.models.sku  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.content_block_definition  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.content_block_translation  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product_type  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product_type_translation  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product_type_content_block  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.variant  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.variant_content  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.content  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product_content_value  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.variant_content_value  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.category  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.category_content  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product_category  # noqa: F401
import src.modules.identity.infrastructure.persistence.models.user  # noqa: F401
import src.modules.identity.infrastructure.persistence.models.user_email  # noqa: F401
import src.modules.identity.infrastructure.persistence.models.cloud_identity
import src.modules.identity.infrastructure.persistence.models.invitation  # noqa: F401
import src.modules.price_lists.infrastructure.persistence  # noqa: F401

# Не удалять имена при удалении модели: autogenerate должен видеть DROP TABLE.
HISTORICAL_TENANT_TABLE_NAMES = frozenset(
    {
        "warehouses",
        "skus",
        "catalog_products",
        "catalog_variants",
        "catalog_product_contents",
        "catalog_product_content_values",
        "catalog_variant_contents",
        "catalog_variant_content_values",
        "catalog_content_block_definitions",
        "catalog_content_block_translations",
        "catalog_product_types",
        "catalog_product_type_translations",
        "catalog_product_type_content_blocks",
        "catalog_categories",
        "catalog_category_contents",
        "catalog_product_categories",
        "contacts",
        "contact_companies",
        "companies",
        "contact_points",
        "contact_point_bindings",
        "contact_point_labels",
        "users",
        "user_emails",
        "cloud_identities",
        "invitations",
        "price_lists",
        "partner_offers",
        "partner_offer_states",
        "price_list_sync_runs",
        "price_list_sync_items",
    }
)
