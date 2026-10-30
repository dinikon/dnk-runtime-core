"""Регистрация статических tenant-моделей и их исторических имён."""

import src.modules.crm.infrastructure.persistence.models.company  # noqa: F401
import src.modules.crm.infrastructure.persistence.models.contact  # noqa: F401
import src.modules.crm.infrastructure.persistence.models.contact_company  # noqa: F401
import src.modules.contact_points.infrastructure.persistence.models.contact_point  # noqa: F401
import src.modules.contact_points.infrastructure.persistence.models.contact_point_binding  # noqa: F401
import src.modules.contact_points.infrastructure.persistence.models.contact_point_label  # noqa: F401
import src.modules.identity.infrastructure.persistence.models.user  # noqa: F401
import src.modules.tenancy.infrastructure.persistence.models.tenant_currency_settings  # noqa: F401
import src.modules.identity.infrastructure.persistence.models.user_email  # noqa: F401
import src.modules.identity.infrastructure.persistence.models.cloud_identity
import src.modules.identity.infrastructure.persistence.models.invitation  # noqa: F401

# Не удалять имена при удалении модели: autogenerate должен видеть DROP TABLE.
HISTORICAL_TENANT_TABLE_NAMES = frozenset(
    {
        "catalog_content_block_definitions",
        "catalog_content_block_translations",
        "catalog_item",
        "catalog_imports",
        "catalog_import_rows",
        "catalog_import_media",
        "catalog_item_content_values",
        "catalog_item_galleries",
        "catalog_item_images",
        "catalog_item_translations",
        "catalog_product_type_content_blocks",
        "catalog_product_type_translations",
        "catalog_product_types",
        "cloud_identities",
        "companies",
        "contact_companies",
        "contact_point_bindings",
        "contact_point_labels",
        "contact_points",
        "contacts",
        "channels",
        "channel_connections",
        "channel_catalog_binding_groups",
        "channel_catalog_binding_items",
        "channel_sync_runs",
        "channel_external_publications",
        "channel_stock_sync_states",
        "channel_product_representations",
        "channel_content_media",
        "channel_content_deliveries",
        "channel_content_feeds",
        "crm_position_history",
        "crm_leads",
        "crm_deals",
        "crm_deal_contacts",
        "crm_deal_companies",
        "crm_baskets",
        "crm_basket_items",
        "funnels",
        "funnel_stages",
        "currency_exchange_rate_books",
        "currency_exchange_rate_quotes",
        "files_buckets",
        "files_providers",
        "files_registry",
        "invitations",
        "tenant_currency_settings",
        "user_emails",
        "users",
    }
)


import src.modules.files.infrastructure.persistence.models.storage_provider  # noqa: F401
import src.modules.files.infrastructure.persistence.models.bucket  # noqa: F401
import src.modules.files.infrastructure.persistence.models.stored_file  # noqa: F401


import src.modules.catalog.infrastructure.persistence.models.catalog_item  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.catalog_item_content_value  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.catalog_item_gallery  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.catalog_item_image  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.catalog_item_translation  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.content_block  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.content_block_translation  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product_type  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product_type_block  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.product_type_translation  # noqa: F401

import src.modules.currency.infrastructure.persistence.models.exchange_rate_book  # noqa: F401
import src.modules.currency.infrastructure.persistence.models.exchange_rate_quote  # noqa: F401

import src.modules.crm.infrastructure.persistence.models.lead  # noqa: F401

import src.modules.crm.infrastructure.persistence.models.deal  # noqa: F401

import src.modules.crm.infrastructure.persistence.models.deal_contact  # noqa: F401

import src.modules.crm.infrastructure.persistence.models.deal_company  # noqa: F401

import src.modules.crm.infrastructure.persistence.models.basket  # noqa: F401

import src.modules.crm.infrastructure.persistence.models.basket_item  # noqa: F401

import src.modules.funnel.infrastructure.persistence.models.funnel  # noqa: F401

import src.modules.funnel.infrastructure.persistence.models.stage  # noqa: F401

import src.modules.catalog.infrastructure.persistence.models.catalog_import  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.catalog_import_row  # noqa: F401
import src.modules.catalog.infrastructure.persistence.models.catalog_import_media  # noqa: F401

import src.modules.channels.infrastructure.persistence.models.channel  # noqa: F401
import src.modules.channels.infrastructure.persistence.models.connection  # noqa: F401
import src.modules.channels.infrastructure.persistence.models.sync_run  # noqa: F401
import src.modules.channels.infrastructure.persistence.models.external_publication  # noqa: F401

import src.modules.crm.infrastructure.persistence.models.position_history  # noqa: F401

import src.modules.channels.infrastructure.persistence.models.catalog_binding_group  # noqa: F401
import src.modules.channels.infrastructure.persistence.models.catalog_binding_item  # noqa: F401

import src.modules.channels.infrastructure.persistence.models.stock_sync  # noqa: F401
import src.modules.channels.infrastructure.persistence.models.product_representation  # noqa: F401
import src.modules.channels.infrastructure.persistence.models.content_media  # noqa: F401

import src.modules.channels.infrastructure.persistence.models.content_delivery  # noqa: F401
import src.modules.channels.infrastructure.persistence.models.content_feed  # noqa: F401
