"""Регистрация статических tenant-моделей и их исторических имён."""

import src.modules.channels.infrastructure.persistence.models.external_publication  # noqa: F401
import src.modules.channels.infrastructure.persistence.models.publication_import_run  # noqa: F401
import src.modules.channels.infrastructure.persistence.models.channel  # noqa: F401
import src.modules.crm.infrastructure.persistence.models.company  # noqa: F401
import src.modules.crm.infrastructure.persistence.models.contact  # noqa: F401
import src.modules.crm.infrastructure.persistence.models.contact_company  # noqa: F401
import src.modules.contact_points.infrastructure.persistence.models.contact_point  # noqa: F401
import src.modules.contact_points.infrastructure.persistence.models.contact_point_binding  # noqa: F401
import src.modules.contact_points.infrastructure.persistence.models.contact_point_label  # noqa: F401
import src.modules.identity.infrastructure.persistence.models.user  # noqa: F401
import src.modules.identity.infrastructure.persistence.models.user_email  # noqa: F401
import src.modules.identity.infrastructure.persistence.models.cloud_identity
import src.modules.identity.infrastructure.persistence.models.invitation  # noqa: F401
import src.modules.price_lists.infrastructure.persistence  # noqa: F401

import src.modules.catalog.infrastructure.persistence.models.content_block  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product_type  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product_type_block  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.variant  # noqa: F401

import src.modules.catalog.infrastructure.persistence.models.content_block_translation  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product_type_translation  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product_translation  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product_content_value  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.variant_translation  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.variant_content_value  # noqa: F401

# Не удалять имена при удалении модели: autogenerate должен видеть DROP TABLE.
HISTORICAL_TENANT_TABLE_NAMES = frozenset(
    {
        "files_providers",
        "files_buckets",
        "files_registry",
        "channels",
        "channel_publications",
        "channel_publication_import_runs",
        "warehouses",
        "warehousing_warehouses",
        "skus",
        "catalog_products",
        "catalog_variants",
        "catalog_product_contents",
        "catalog_product_content_values",
        "catalog_variant_contents",
        "catalog_product_translations",
        "catalog_variant_translations",
        "catalog_variant_content_values",
        "catalog_content_block_definitions",
        "catalog_content_block_translations",
        "catalog_product_types",
        "catalog_product_type_translations",
        "catalog_product_type_content_blocks",
        "catalog_categories",
        "catalog_category_contents",
        "catalog_product_categories",
        "catalog_attributes",
        "catalog_attribute_options",
        "catalog_attribute_translations",
        "catalog_attribute_option_translations",
        "catalog_product_axes",
        "catalog_product_axis_options",
        "catalog_variant_selections",
        "catalog_product_default_selections",
        "catalog_category_translations",
        "catalog_tags",
        "catalog_tag_translations",
        "catalog_product_tags",
        "catalog_product_attribute_values",
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
import src.modules.catalog.infrastructure.persistence.models.attribute  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.attribute_translation  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.attribute_option  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.attribute_option_translation  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product_axis  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product_axis_option  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.variant_selection  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product_default_selection  # noqa: F401

import src.modules.files.infrastructure.persistence.models.storage_provider  # noqa: F401
import src.modules.files.infrastructure.persistence.models.bucket  # noqa: F401
import src.modules.files.infrastructure.persistence.models.stored_file  # noqa: F401

import src.modules.catalog.infrastructure.persistence.models.category  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.category_translation  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.tag  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.tag_translation  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product_category  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product_tag  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product_attribute_value  # noqa: F401
