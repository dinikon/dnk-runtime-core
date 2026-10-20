"""Контракт JSON-снимка и идентичности публикации без сети и Catalog."""

from dataclasses import replace
from datetime import datetime, date, timezone
from decimal import Decimal
import unittest
from uuid import uuid4
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.error import (
    ChannelsValidationError,
    ChannelsConflictError,
)
from src.modules.channels.domain.external_publication.aggregate import (
    ExternalPublication,
)
from src.modules.channels.domain.external_publication.value_object.payload import (
    PublicationPayloadVO,
)
from src.modules.channels.domain.external_publication.value_object.meta import (
    PublicationMetaVO,
)
from src.modules.channels.application.plugin_contract import (
    ResourceSettingsDTO,
    ObservedPublicationDTO,
)
from src.modules.channels.infrastructure.plugin.prom.core_normalizer import (
    normalize_product as prom,
)
from src.modules.channels.infrastructure.plugin.woocommerce.core_normalizer import (
    normalize_product as woo,
)
from src.modules.channels.infrastructure.external_publication.persistence.mapper import (
    ExternalPublicationMapper,
)


class PublicationPayloadTests(unittest.TestCase):
    """Проверяет потерю точности, локалей и identity на границах хранения."""

    def observed(self) -> ObservedPublicationDTO:
        """Создаёт снимок двух локалей с действующей акцией и нулевым остатком."""
        return prom(
            {
                "id": 123,
                "external_id": "old-import-key",
                "sku": "ABC",
                "name_multilang": {"ru": "Название", "uk": "Назва"},
                "description": "Legacy body",
                "price": "123.450000000001",
                "currency": "UAH",
                "quantity_in_stock": 0,
                "presence": "available",
                "discount": {
                    "type": "amount",
                    "value": "123.450000000001",
                    "date_start": "19.10.2026",
                    "date_end": "21.10.2026",
                },
            },
            ResourceSettingsDTO(
                "https://my.prom.ua", {"locales": ["ru", "uk"], "currency": "UAH"}
            ),
            observed_on=date(2026, 10, 20),
        )

    def test_money_locales_period_and_private_import_identity(self) -> None:
        """Строковые деньги, обе локали и import key независимы от native ID."""
        row = self.observed()
        document = row.payload.to_document()
        self.assertEqual(document["pricing"]["regular"], "123.450000000001")
        self.assertEqual(document["pricing"]["sale"], "0")
        self.assertEqual(document["stock"]["quantity"], "0")
        self.assertEqual(document["titles"], {"ru": "Название", "uk": "Назва"})
        self.assertEqual(document["pricing"]["promotion"]["starts_at"], "2026-10-19")
        self.assertEqual(row.external_id, "123")
        self.assertEqual(row.meta.provider["import_key"], "old-import-key")
        self.assertNotIn("provider_external_id", row.meta.provider)
        self.assertEqual(PublicationPayloadVO.from_document(document), row.payload)

    def test_unknown_values_and_missing_import_key_stay_readable(self) -> None:
        """Пустой import key не блокирует наблюдение и не превращает null в ноль."""
        row = prom(
            {"id": 124, "name": "Read only"},
            ResourceSettingsDTO(
                "https://my.prom.ua", {"locales": ["ru", "uk"], "currency": "UAH"}
            ),
            observed_on=date(2026, 10, 20),
        )
        self.assertIsNone(row.meta.provider["import_key"])
        self.assertIsNone(row.payload.to_document()["stock"]["quantity"])
        self.assertIsNone(row.payload.to_document()["pricing"]["regular"])
        self.assertIn("quantity_not_exposed", row.meta.read_issues)
        self.assertNotIn("uk", dict(row.payload.titles))

    def test_woo_variation_context_and_promotion_roundtrip(self) -> None:
        """Parent ID и GMT-период переживают JSON roundtrip вариации."""
        row = woo(
            {
                "id": 55,
                "name": "Variation",
                "regular_price": "20",
                "sale_price": "0",
                "date_on_sale_from_gmt": "2026-10-19T12:00:00",
                "date_on_sale_to_gmt": "2026-10-21T12:00:00",
                "stock_status": "instock",
            },
            ResourceSettingsDTO(
                "https://woo.example", {"locales": ["uk"], "currency": "UAH"}
            ),
            10,
        )
        self.assertEqual(row.resource_type, "variation")
        self.assertEqual(row.meta.provider["parent_id"], 10)
        self.assertEqual(row.payload.promotion.starts_at, "2026-10-19T12:00:00+00:00")
        self.assertEqual(
            PublicationMetaVO.from_document(row.meta.to_document()), row.meta
        )
        copy = row.meta.provider
        copy["parent_id"] = 999
        self.assertEqual(row.meta.provider["parent_id"], 10)

    def test_unknown_locale_is_preserved_without_fallback(self) -> None:
        """Исторический заголовок без локали не становится переводом другого языка."""
        payload = replace(
            self.observed().payload, titles=(("und", "Unknown"),), display_locale=None
        )
        self.assertEqual(
            PublicationPayloadVO.from_document(payload.to_document()).title, "Unknown"
        )
        self.assertIsNone(replace(payload, display_locale="uk").title)

    def test_revision_changes_only_with_semantic_snapshot_change(self) -> None:
        """Разный масштаб Decimal не инвалидирует связи и подготовленные команды."""
        row = self.observed()
        now = datetime.now(timezone.utc)
        entity = ExternalPublication.create(
            EntityIdVO(uuid4()),
            EntityIdVO(uuid4()),
            row.resource_type,
            row.external_id,
            row.payload,
            row.meta,
            row.source_updated_at,
            EntityIdVO(uuid4()),
            now,
        )
        restored = ExternalPublicationMapper.to_domain(
            ExternalPublicationMapper.to_values(entity)
        )
        restored.observe(
            row.resource_type,
            row.external_id,
            replace(row.payload, quantity=Decimal("0.000000000000")),
            row.meta,
            row.source_updated_at,
            EntityIdVO(uuid4()),
            now,
        )
        self.assertEqual(restored.id, entity.id)
        self.assertEqual(restored.observed_revision, 1)
        restored.observe(
            row.resource_type,
            row.external_id,
            replace(row.payload, sku="CHANGED"),
            row.meta,
            row.source_updated_at,
            EntityIdVO(uuid4()),
            now,
        )
        self.assertEqual(restored.observed_revision, 2)
        with self.assertRaises(ChannelsConflictError):
            restored.observe(
                row.resource_type,
                "999",
                row.payload,
                row.meta,
                row.source_updated_at,
                EntityIdVO(uuid4()),
                now,
            )

    def test_corrupt_documents_and_nonfinite_numbers_are_rejected(self) -> None:
        """Неизвестная версия и некорректные JSON-значения не принимаются молча."""
        for document in (
            {"schema_version": 2},
            {"schema_version": 1},
            {"schema_version": 1, "titles": []},
        ):
            with self.assertRaises(ChannelsValidationError):
                PublicationPayloadVO.from_document(document)
        for number in (Decimal("NaN"), Decimal("Infinity"), Decimal("0.0000000000001")):
            with self.assertRaises(ChannelsValidationError):
                replace(self.observed().payload, price=number)
        with self.assertRaises(ChannelsValidationError):
            PublicationMetaVO.create("prom.read.v2", {"bad": float("nan")}, ())

    def test_json_numbers_cannot_silently_replace_decimal_strings(self) -> None:
        """JSON float и bool отвергаются до преобразования в Decimal."""
        for value in (1.1, True, 1):
            document = self.observed().payload.to_document()
            document["pricing"]["regular"] = value
            with self.assertRaises(ChannelsValidationError):
                PublicationPayloadVO.from_document(document)
        document = self.observed().payload.to_document()
        document["schema_version"] = True
        with self.assertRaises(ChannelsValidationError):
            PublicationPayloadVO.from_document(document)

    def test_full_numeric_range_is_not_rounded_by_decimal_context(self) -> None:
        """Верхняя допустимая граница NUMERIC(30,12) сохраняется целиком."""
        number = "999999999999999999.999999999999"
        row = woo(
            {
                "id": 57,
                "name": "Precise",
                "regular_price": number,
                "stock_status": "instock",
            },
            ResourceSettingsDTO(
                "https://woo.example", {"locales": ["uk"], "currency": "UAH"}
            ),
        )
        self.assertEqual(row.payload.to_document()["pricing"]["regular"], number)
        self.assertEqual(
            PublicationPayloadVO.from_document(row.payload.to_document()).price,
            Decimal(number),
        )
