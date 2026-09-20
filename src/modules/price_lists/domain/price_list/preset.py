from typing import Any

PROM_XML_SOURCE = {"item_path": "yml_catalog.shop.offers.offer"}
PROM_XML_MAPPING = {
    "external_id": {"selector": "@id", "required": True, "trim": True},
    "sku": {"selector": "vendorCode", "required": True, "trim": True},
    "title": {"selector": "name", "required": True, "trim": True},
    "purchase_price": {"selector": "price", "type": "decimal", "required": True},
    "rrp": {"selector": "priceRRP", "type": "decimal"},
    "currency": {"selector": "currencyId", "default": "UAH"},
    "availability": {
        "selector": "@available",
        "default": "out_of_stock",
        "map": {
            "склад": "in_stock",
            "true": "in_stock",
            "false": "out_of_stock",
            "": "out_of_stock",
        },
    },
    "quantity": {"constant": None},
}


def prom_xml_config() -> tuple[dict[str, Any], dict[str, Any]]:
    return dict(PROM_XML_SOURCE), {
        key: dict(value) for key, value in PROM_XML_MAPPING.items()
    }


__all__ = ["prom_xml_config"]
