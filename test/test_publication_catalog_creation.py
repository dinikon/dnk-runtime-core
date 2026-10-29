"""Контракты полного чтения площадок и правила структуры создания Catalog."""

import unittest
from uuid import uuid4
from decimal import Decimal
from datetime import UTC, datetime
from src.modules.channels.application.external_publication.catalog_details import (
    PublicationLookup,
)
from src.modules.channels.domain.channel.value_object.connection_config import (
    ConnectionConfigVO,
)
from src.modules.channels.infrastructure.platforms.prom.platform import PromPlatform
from src.modules.channels.infrastructure.platforms.woocommerce.platform import (
    WooCommercePlatform,
)
from src.modules.channels.infrastructure.platforms.rozetka.platform import (
    RozetkaPlatform,
)
from src.modules.channels.infrastructure.http import JsonHttpResponse
from src.modules.channels.application.error import VerificationFailure
from pydantic import ValidationError


class DetailsHttp:
    """Ограниченные реальные envelopes без сетевого доступа."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    async def request(self, method, url, *, headers=None, body=None):
        self.calls.append((method, url, headers))
        key = next(k for k in self.responses if k in url)
        return self.responses[key]

    async def request_response(self, method, url, *, headers=None, body=None):
        data = await self.request(method, url, headers=headers, body=body)
        return JsonHttpResponse(data, {"x-wp-totalpages": "1"})


def lookup(external="20", kind="simple", parent=None, resource="product", native=None):
    return PublicationLookup(uuid4(), resource, external, kind, parent, 1, native or {})


class PublicationDetailsTests(unittest.IsolatedAsyncioTestCase):
    async def test_prom_base_is_sellable_both_translations_and_full_gallery(self):
        root = lookup()
        child = lookup("21", "variant", root.id)
        first = {
            "id": 20,
            "name_multilang": {"uk": "База", "ru": "Основа"},
            "description_multilang": {"ua": "Опис", "ru": "Описание"},
            "sku": "BASE",
            "presence": "available",
            "quantity_in_stock": 4,
            "images": [
                {"url": "https://img.example/a.png"},
                {"url": "https://img.example/b.png"},
            ],
        }
        second = {
            "id": 21,
            "is_variation": True,
            "variation_base_id": 20,
            "name_multilang": {"uk": "Варіант"},
            "presence": "not_available",
        }
        http = DetailsHttp(
            {
                "products/list": {"products": [first, second]},
                "products/20": {"product": first},
                "products/21": {"product": second},
            }
        )
        details = await PromPlatform(http).get_details(
            config=ConnectionConfigVO.create(
                version=1, endpoint="https://my.prom.ua", settings={}
            ),
            credentials=b'{"token":"real-secret"}',
            publications=(root, child),
        )
        self.assertEqual(len(details.products), 2)
        base = details.products[0]
        self.assertEqual(
            (base.kind, base.quantity, base.sku), ("simple", Decimal(4), "BASE")
        )
        self.assertEqual(
            [(t.locale, t.body) for t in base.translations],
            [("uk", "Опис"), ("ru", "Описание")],
        )
        self.assertEqual(len(base.image_urls), 2)
        self.assertIsNone(details.products[1].translations[1].title)
        self.assertTrue(
            all(
                c[0] == "GET" and c[2]["Authorization"] == "Bearer real-secret"
                for c in http.calls
            )
        )

    async def test_prom_downloads_original_gallery_images_instead_of_api_thumbnails(
        self,
    ):
        first = "https://images.prom.ua/123_w200_h200_product.jpg"
        second = "https://images.prom.ua/124_w640_h640_product-back.png?version=2"
        raw = {
            "id": 20,
            "main_image": first,
            "images": [
                {
                    "id": 123,
                    "url": first,
                    "thumbnail_url": "https://images.prom.ua/123_w100_h100_product.jpg",
                },
                {"id": 124, "url": second},
                {"id": 125, "url": "https://images.prom.ua/125_original.jpg"},
                {"id": 126, "url": "https://shop.example/126_w200_h200_product.jpg"},
            ],
        }
        http = DetailsHttp({"products/20": {"product": raw}})
        details = await PromPlatform(http).get_details(
            config=ConnectionConfigVO.create(
                version=1, endpoint="https://my.prom.ua", settings={}
            ),
            credentials=b'{"token":"secret"}',
            publications=(lookup(),),
        )
        self.assertEqual(
            details.products[0].image_urls,
            (
                "https://images.prom.ua/123_product.jpg",
                "https://images.prom.ua/124_product-back.png?version=2",
                "https://images.prom.ua/125_original.jpg",
                "https://shop.example/126_w200_h200_product.jpg",
            ),
        )
        self.assertEqual(raw["images"][0]["url"], first)
        self.assertEqual(raw["main_image"], first)

    async def test_prom_main_image_fallback_only_changes_known_cdn_image_paths(self):
        cases = (
            (
                "https://images.prom.ua/123_w200_h200_product.jpg",
                "https://images.prom.ua/123_product.jpg",
            ),
            (
                "https://images.prom.ua.evil.example/123_w200_h200_product.jpg",
                "https://images.prom.ua.evil.example/123_w200_h200_product.jpg",
            ),
            (
                "https://images.prom.ua/folder/123_w200_h200_product.jpg",
                "https://images.prom.ua/folder/123_w200_h200_product.jpg",
            ),
            (
                "https://images.prom.ua/123_product_w200_h200_detail.jpg",
                "https://images.prom.ua/123_product_w200_h200_detail.jpg",
            ),
            (None, None),
        )
        for source, expected in cases:
            with self.subTest(source=source):
                http = DetailsHttp(
                    {"products/20": {"product": {"id": 20, "main_image": source}}}
                )
                details = await PromPlatform(http).get_details(
                    config=ConnectionConfigVO.create(
                        version=1, endpoint="https://my.prom.ua", settings={}
                    ),
                    credentials=b'{"token":"secret"}',
                    publications=(lookup(),),
                )
                self.assertEqual(
                    details.products[0].image_urls, (expected,) if expected else ()
                )

    async def test_woo_details_variable_stock_units_and_parent_content(self):
        root = lookup(kind="variable")
        child = lookup("21", "variant", root.id, "variation")
        http = DetailsHttp(
            {
                "/variations?": [
                    {
                        "id": 21,
                        "sku": "S",
                        "manage_stock": "parent",
                        "stock_status": "instock",
                        "description": "",
                        "regular_price": "100.123456",
                        "sale_price": "0",
                        "date_on_sale_from_gmt": "2026-10-01T00:00:00",
                        "date_on_sale_to_gmt": "2026-10-31T00:00:00",
                        "image": {"src": "https://img.example/s.png"},
                    }
                ],
                "/products/20": {
                    "id": 20,
                    "type": "variable",
                    "name": "Parent",
                    "description": "<p>Body</p>",
                    "manage_stock": True,
                    "stock_quantity": 10,
                    "backorders": "notify",
                    "variations": [21],
                    "images": [{"src": "https://img.example/p.png"}],
                    "weight": "2",
                    "dimensions": {"width": "4"},
                },
                "/settings/products": [
                    {"id": "woocommerce_weight_unit", "value": "kg"},
                    {"id": "woocommerce_dimension_unit", "value": "cm"},
                    {"id": "woocommerce_enable_reviews", "value": "yes"},
                ],
            }
        )
        details = await WooCommercePlatform(http).get_details(
            config=ConnectionConfigVO.create(
                version=1, endpoint="https://shop.example", settings={"locale": "en"}
            ),
            credentials=b'{"consumer_key":"key","consumer_secret":"secret"}',
            publications=(root, child),
        )
        parent, variant = details.products
        self.assertEqual(
            (parent.quantity, parent.backorders, parent.weight, parent.width),
            (Decimal(10), "notify", Decimal(2), Decimal(4)),
        )
        self.assertEqual(parent.translations[0].locale, "en")
        self.assertFalse(variant.manage_stock)
        self.assertIsNone(variant.translations[0].body)
        self.assertEqual(variant.resource_type, "variation")
        self.assertIsNone(parent.regular_price)
        self.assertIsNone(parent.sale_price)
        self.assertEqual(variant.regular_price, Decimal("100.123456"))
        self.assertEqual(variant.sale_price, Decimal(0))
        self.assertEqual(variant.currency, "UAH")
        self.assertEqual(variant.date_on_sale_from, datetime(2026, 10, 1, tzinfo=UTC))
        self.assertEqual(variant.date_on_sale_to, datetime(2026, 10, 31, tzinfo=UTC))
        self.assertTrue(http.calls[0][2]["Authorization"].startswith("Basic "))

    async def test_woo_does_not_accept_incomplete_variation_pagination(self):
        http = DetailsHttp(
            {
                "/variations?": [],
                "/products/20": {"id": 20, "type": "variable", "variations": [21]},
            }
        )
        with self.assertRaises(VerificationFailure):
            await WooCommercePlatform(http).get_details(
                config=ConnectionConfigVO.create(
                    version=1, endpoint="https://shop.example", settings={}
                ),
                credentials=b'{"consumer_key":"key","consumer_secret":"secret"}',
                publications=(lookup(kind="variable"),),
            )

    async def test_rozetka_documented_envelope_and_stable_identity_without_rz_id(self):
        root = lookup(
            "3:offer",
            resource="source_offer",
            native={"item_id": 42, "sync_source_id": 3},
        )
        http = DetailsHttp(
            {
                "/goods/details?": {
                    "success": True,
                    "content": {
                        "item": [
                            {
                                "sync_source_id": 3,
                                "price_offer_id": "offer",
                                "item_id": 42,
                                "rz_item_id": None,
                                "name_ua": "Назва",
                                "name_ru": "Название",
                                "description_ua": "Опис",
                                "description": "Описание",
                                "available": 1,
                                "photo": ["https://img.example/a.png"],
                                "price": 599,
                                "price_old": 799,
                                "price_promo": 499,
                            }
                        ]
                    },
                }
            }
        )
        details = await RozetkaPlatform(http).get_details(
            config=ConnectionConfigVO.create(
                version=1, endpoint="https://api-seller.rozetka.com.ua", settings={}
            ),
            credentials=b'{"token":"token"}',
            publications=(root,),
        )
        self.assertEqual(details.products[0].external_id, "3:offer")
        self.assertEqual(
            [t.body for t in details.products[0].translations], ["Опис", "Описание"]
        )
        self.assertIn("item_id=42", http.calls[0][1])
        self.assertIn("sync_source_id=3", http.calls[0][1])
        self.assertEqual(details.products[0].regular_price, Decimal(799))
        self.assertEqual(details.products[0].sale_price, Decimal(499))
        self.assertEqual(details.products[0].currency, "UAH")

    async def test_prom_prices_and_calendar_sale_period(self):
        for discount, expected in (
            ({"type": "percent", "value": 25}, "75"),
            ({"type": "amount", "value": 100}, "0"),
        ):
            with self.subTest(discount=discount):
                http = DetailsHttp(
                    {
                        "products/20": {
                            "product": {
                                "id": 20,
                                "price": "100",
                                "currency": "USD",
                                "discount": {
                                    **discount,
                                    "date_start": "28.03.2026",
                                    "date_end": "29.03.2026",
                                },
                            }
                        }
                    }
                )
                details = await PromPlatform(http).get_details(
                    config=ConnectionConfigVO.create(
                        version=1, endpoint="https://my.prom.ua", settings={}
                    ),
                    credentials=b'{"token":"secret"}',
                    publications=(lookup(),),
                )
                product = details.products[0]
                self.assertEqual(product.regular_price, Decimal(100))
                self.assertEqual(product.sale_price, Decimal(expected))
                self.assertEqual(product.currency, "UAH")
                self.assertEqual(
                    product.date_on_sale_from, datetime(2026, 3, 27, 22, tzinfo=UTC)
                )
                self.assertEqual(
                    product.date_on_sale_to, datetime(2026, 3, 29, 21, tzinfo=UTC)
                )

    async def test_rozetka_current_price_becomes_sale_when_old_price_is_present(self):
        root = lookup("3:offer", resource="source_offer", native={"item_id": 42})
        http = DetailsHttp(
            {
                "/goods/details?": {
                    "success": True,
                    "content": {
                        "item": {
                            "sync_source_id": 3,
                            "price_offer_id": "offer",
                            "price": 599,
                            "price_old": 799,
                        }
                    },
                }
            }
        )
        details = await RozetkaPlatform(http).get_details(
            config=ConnectionConfigVO.create(
                version=1, endpoint="https://api-seller.rozetka.com.ua", settings={}
            ),
            credentials=b'{"token":"secret"}',
            publications=(root,),
        )
        self.assertEqual(details.products[0].regular_price, Decimal(799))
        self.assertEqual(details.products[0].sale_price, Decimal(599))

    async def test_rozetka_without_identifiers_is_explicit_failure(self):
        with self.assertRaises(VerificationFailure):
            await RozetkaPlatform(DetailsHttp({})).get_details(
                config=ConnectionConfigVO.create(
                    version=1, endpoint="https://api-seller.rozetka.com.ua", settings={}
                ),
                credentials=b'{"token":"token"}',
                publications=(lookup(resource="source_offer"),),
            )

    async def test_rozetka_details_accept_preview_string_and_preserve_full_gallery(
        self,
    ):
        gallery = "https://img.example/original.png"
        preview = "https://img.example/preview.png"
        cases = (
            ([gallery], preview, (gallery,)),
            ([], preview, (preview,)),
            ([], [preview], (preview,)),
            ([], "", ()),
        )
        for photos, previews, expected in cases:
            with self.subTest(photos=photos, previews=previews):
                root = lookup(
                    "3:offer",
                    resource="source_offer",
                    native={"item_id": 42, "sync_source_id": 3},
                )
                raw = {
                    "sync_source_id": 3,
                    "price_offer_id": "offer",
                    "item_id": 42,
                    "name_ua": "Назва",
                    "name_ru": "Название",
                    "description_ua": "Опис",
                    "description": "Описание",
                    "photo": photos,
                    "photo_preview": previews,
                    "stock_quantity": 5,
                }
                http = DetailsHttp(
                    {
                        "/goods/details?": {
                            "success": True,
                            "content": {"item": [raw]},
                        }
                    }
                )
                details = await RozetkaPlatform(http).get_details(
                    config=ConnectionConfigVO.create(
                        version=1,
                        endpoint="https://api-seller.rozetka.com.ua",
                        settings={},
                    ),
                    credentials=b'{"token":"secret"}',
                    publications=(root,),
                )
                self.assertEqual(details.products[0].image_urls, expected)
                self.assertEqual(details.products[0].quantity, Decimal(5))
                self.assertEqual(details.products[0].translations[0].body, "Опис")
                self.assertEqual(raw["photo_preview"], previews)

    async def test_rozetka_details_do_not_coerce_invalid_preview_type(self):
        root = lookup(
            "3:offer",
            resource="source_offer",
            native={"item_id": 42, "sync_source_id": 3},
        )
        http = DetailsHttp(
            {
                "/goods/details?": {
                    "success": True,
                    "content": {
                        "item": {
                            "sync_source_id": 3,
                            "price_offer_id": "offer",
                            "photo_preview": 123,
                        }
                    },
                }
            }
        )
        with self.assertRaises(ValidationError):
            await RozetkaPlatform(http).get_details(
                config=ConnectionConfigVO.create(
                    version=1, endpoint="https://api-seller.rozetka.com.ua", settings={}
                ),
                credentials=b'{"token":"secret"}',
                publications=(root,),
            )
