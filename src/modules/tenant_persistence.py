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
import src.modules.catalog.infrastructure.persistence.models.variant  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.content  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.attribute  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.attribute_option  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.attribute_content  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.option_content  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.variant_selection  # noqa: F401
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
        "catalog_attributes",
        "catalog_attribute_options",
        "catalog_attribute_contents",
        "catalog_option_contents",
        "catalog_variant_selections",
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
