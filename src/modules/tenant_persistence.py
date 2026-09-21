"""Регистрация статических tenant-моделей и их исторических имён."""

import src.modules.inventory.infrastructure.persistence  # noqa: F401
import src.modules.identity.infrastructure.persistence  # noqa: F401
import src.modules.price_lists.infrastructure.persistence  # noqa: F401
import src.modules.currency.infrastructure.persistence  # noqa: F401

# Не удалять имена при удалении модели: autogenerate должен видеть DROP TABLE.
HISTORICAL_TENANT_TABLE_NAMES = frozenset(
    {
        "warehouses",
        "users",
        "user_emails",
        "cloud_identities",
        "invitations",
        "price_lists",
        "partner_offers",
        "partner_offer_states",
        "price_list_sync_runs",
        "price_list_sync_items",
        "currency_policy",
        "currency_resolution_failure",
        "enabled_currency",
        "functional_currency_period",
        "manual_exchange_rate",
        "partner_offer_money_snapshots",
    }
)
