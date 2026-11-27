from src.modules.feed_builder.domain.publication.value_object.feed_publication_version import (
    FeedPublicationVersionVO,
)

"""Состояния публикаций, генераций и ключей доступа без I/O и переходов поведения."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
import unittest

from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.money import MoneyVO
from src.modules.feed_builder.domain.feed.value_object.price_amount import PriceAmountVO
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.value_object.field_id import FieldIdVO
from src.modules.feed_builder.domain.publication.aggregate import FeedPublication
from src.modules.feed_builder.domain.publication.enum.publication_status import (
    PublicationStatus,
)
from src.modules.feed_builder.domain.publication.enum.override_mode import OverrideMode
from src.modules.feed_builder.domain.publication.error import (
    InvalidPublicationValueError,
    DuplicateFieldOverrideError,
)
from src.modules.feed_builder.domain.publication.value_object.feed_publication_id import (
    FeedPublicationIdVO,
)
from src.modules.feed_builder.domain.publication.value_object.catalog_product_reference import (
    CatalogProductReferenceVO,
)
from src.modules.feed_builder.domain.publication.value_object.field_override import (
    FieldOverrideVO,
)
from src.modules.feed_builder.domain.access_key.aggregate import FeedAccessKey
from src.modules.feed_builder.domain.access_key.enum.access_key_status import (
    AccessKeyStatus,
)
from src.modules.feed_builder.domain.access_key.error import InvalidAccessKeyValueError
from src.modules.feed_builder.domain.access_key.value_object.access_key_name import AccessKeyNameVO
from src.modules.feed_builder.domain.access_key.value_object.feed_access_key_id import (
    FeedAccessKeyIdVO,
)
from src.modules.feed_builder.domain.access_key.value_object.access_token_hash import (
    AccessTokenHashVO,
)

NOW = datetime(2026, 11, 21, 10, tzinfo=UTC)
STARTED = NOW + timedelta(minutes=1)
FINISHED = NOW + timedelta(minutes=2)
UAH = CurrencyVO("UAH")


def properties(value: object) -> dict[str, object]:
    """Извлекает все объявленные поля для проверки полного восстановления."""
    return {field.name: getattr(value, field.name) for field in fields(value)}


def restored_properties(values: dict[str, object]) -> dict[str, object]:
    """Сопоставляет именованный аргумент фабрики с хранимым идентификатором."""
    return {
        ("id" if key == "identifier" else key): value for key, value in values.items()
    }


class FeedPublicationDomainTests(unittest.TestCase):
    """Проверяет выбранные позиции и независимые ручные значения."""

    def test_create_simple_and_selected_variant(self) -> None:
        """Простой товар и выбранный вариант создают отдельные ENABLED-публикации."""
        item_id = EntityIdVO(uuid4())
        for reference in (
            CatalogProductReferenceVO(item_id),
            CatalogProductReferenceVO(item_id, EntityIdVO(uuid4())),
        ):
            with self.subTest(reference=reference):
                identifier = FeedPublicationIdVO(uuid4())
                feed_id = FeedIdVO(uuid4())
                result = FeedPublication.create(
                    identifier=identifier,
                    feed_id=feed_id,
                    product_reference=reference,
                    now=NOW,
                )
                self.assertEqual(
                    properties(result),
                    dict(
                        id=identifier,
                        feed_id=feed_id,
                        product_reference=reference,
                        status=PublicationStatus.ENABLED,
                        version=FeedPublicationVersionVO(1),
                        overrides=(),
                        created_at=NOW,
                        updated_at=NOW,
                    ),
                )

    def test_restore_preserves_every_status_and_all_fields(self) -> None:
        """История и явное пустое значение восстанавливаются без текущей схемы."""
        overrides = (
            FieldOverrideVO(FieldIdVO(uuid4()), "Длинный\nтекст"),
            FieldOverrideVO(FieldIdVO(uuid4()), PriceAmountVO(Decimal("123.456789"))),
            FieldOverrideVO(FieldIdVO(uuid4()), None),
            FieldOverrideVO(FieldIdVO(uuid4()), ""),
        )
        for status in PublicationStatus:
            values = dict(
                identifier=FeedPublicationIdVO(uuid4()),
                feed_id=FeedIdVO(uuid4()),
                product_reference=CatalogProductReferenceVO(
                    EntityIdVO(uuid4()), EntityIdVO(uuid4())
                ),
                status=status,
                version=FeedPublicationVersionVO(17),
                overrides=overrides,
                created_at=NOW,
                updated_at=FINISHED,
            )
            result = FeedPublication.restore(**values)
            self.assertEqual(properties(result), restored_properties(values))
            self.assertIs(result.overrides[2].value, None)
            self.assertIs(result.overrides[0].mode, OverrideMode.MANUAL)

    def test_duplicate_overrides_are_rejected_with_path(self) -> None:
        """Один field_id не может иметь два индивидуальных значения."""
        override = FieldOverrideVO(FieldIdVO(uuid4()), "Первое")
        result = FeedPublication.create(
            identifier=FeedPublicationIdVO(uuid4()),
            feed_id=FeedIdVO(uuid4()),
            product_reference=CatalogProductReferenceVO(EntityIdVO(uuid4())),
            now=NOW,
        )
        values = properties(result)
        values["identifier"] = values.pop("id")
        with self.assertRaises(DuplicateFieldOverrideError) as raised:
            FeedPublication.restore(
                **(values | {"overrides": (override, replace(override, value=None))})
            )
        self.assertEqual(raised.exception.path, ("overrides", 1, "field_id"))

    def test_reference_requires_ids_and_distinct_parent_variant(self) -> None:
        """Неверные ссылки отклоняются без импорта Catalog."""
        identifier = EntityIdVO(uuid4())
        for item_id, variant_id in (
            (None, None),
            (str(identifier), None),
            (identifier, str(identifier)),
            (identifier, identifier),
            (identifier, FeedIdVO(identifier.uuid)),
        ):
            with self.subTest(item=item_id, variant=variant_id):
                with self.assertRaises(InvalidPublicationValueError):
                    CatalogProductReferenceVO(item_id, variant_id)

    def test_override_rejects_untyped_values_and_mutable_structures(self) -> None:
        """JSON, сырой Decimal, Shared MoneyVO и неподдержанные скаляры отклоняются."""
        for value in (
            [],
            {},
            1.2,
            Decimal("12"),
            object(),
            MoneyVO(Decimal("12"), UAH),
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidPublicationValueError),
            ):
                FieldOverrideVO(FieldIdVO(uuid4()), value)
        with self.assertRaises(InvalidPublicationValueError):
            FieldOverrideVO(EntityIdVO(uuid4()), "value")
        with self.assertRaises(TypeError):
            FieldOverrideVO(FieldIdVO(uuid4()), "value", mode=OverrideMode.MANUAL)

    def test_restore_rejects_invalid_properties_and_dates(self) -> None:
        """Restore проверяет типы, временную зону и порядок дат так же, как create."""
        result = FeedPublication.create(
            identifier=FeedPublicationIdVO(uuid4()),
            feed_id=FeedIdVO(uuid4()),
            product_reference=CatalogProductReferenceVO(EntityIdVO(uuid4())),
            now=NOW,
        )
        values = properties(result)
        values["identifier"] = values.pop("id")
        for changes in (
            {"identifier": FeedIdVO(uuid4())},
            {"feed_id": EntityIdVO(uuid4())},
            {"product_reference": {}},
            {"status": "ENABLED"},
            {"overrides": {}},
            {"overrides": ("bad",)},
            {"created_at": NOW.replace(tzinfo=None)},
            {"updated_at": NOW - timedelta(seconds=1)},
            {"updated_at": "now"},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidPublicationValueError),
            ):
                FeedPublication.restore(**(values | changes))
        with self.assertRaises(InvalidPublicationValueError):
            FeedPublication.create(
                identifier=result.id,
                feed_id=result.feed_id,
                product_reference=result.product_reference,
                now=NOW.replace(tzinfo=None),
            )

    def test_publication_freezes_input_collection(self) -> None:
        """Изменение исходного списка не меняет восстановленную публикацию."""
        overrides = [FieldOverrideVO(FieldIdVO(uuid4()), "Текст")]
        result = FeedPublication.restore(
            identifier=FeedPublicationIdVO(uuid4()),
            feed_id=FeedIdVO(uuid4()),
            product_reference=CatalogProductReferenceVO(EntityIdVO(uuid4())),
            status=PublicationStatus.PAUSED,
            version=FeedPublicationVersionVO(1),
            overrides=overrides,
            created_at=NOW,
            updated_at=FINISHED,
        )
        overrides.clear()
        self.assertEqual(len(result.overrides), 1)
        with self.assertRaises(FrozenInstanceError):
            result.status = PublicationStatus.ENABLED
        with self.assertRaises(FrozenInstanceError):
            result.overrides[0].value = "Изменение"

    def test_price_override_preserves_precision_without_own_currency(self) -> None:
        """Ручная сумма не дублирует метку поля и не округляется shared MoneyVO."""
        amount = PriceAmountVO(Decimal("123.456789"))
        identifier = FieldIdVO(uuid4())
        values = dict(
            identifier=FeedPublicationIdVO(uuid4()),
            feed_id=FeedIdVO(uuid4()),
            product_reference=CatalogProductReferenceVO(EntityIdVO(uuid4())),
            status=PublicationStatus.ENABLED,
            version=FeedPublicationVersionVO(1),
            overrides=(FieldOverrideVO(identifier, amount),),
            created_at=NOW,
            updated_at=FINISHED,
        )
        restored = FeedPublication.restore(**values)
        self.assertEqual(restored.overrides[0].value.amount, Decimal("123.456789"))
        self.assertEqual({item.name for item in fields(amount)}, {"amount"})
        with self.assertRaises(FrozenInstanceError):
            amount.amount = Decimal("0")


class FeedAccessKeyDomainTests(unittest.TestCase):
    """Проверяет состояние ключей без генерации или проверки секрета."""

    def test_create_sets_all_fields_and_hides_digest(self) -> None:
        """Новый ключ активен, не отозван и не раскрывает digest через repr."""
        identifier = FeedAccessKeyIdVO(uuid4())
        feed_id = FeedIdVO(uuid4())
        digest = AccessTokenHashVO(b"h" * 32)
        result = FeedAccessKey.create(
            identifier=identifier, feed_id=feed_id, token_hash=digest, now=NOW,
            name=AccessKeyNameVO("Площадка"),
        )
        self.assertEqual(
            properties(result),
            dict(
                id=identifier,
                feed_id=feed_id,
                token_hash=digest,
                status=AccessKeyStatus.ACTIVE,
                created_at=NOW,
                revoked_at=None,
                name=AccessKeyNameVO("Площадка"),
                expires_at=None,
            ),
        )
        self.assertNotIn(repr(digest.value), repr(result))
        with self.assertRaises(FrozenInstanceError):
            result.status = AccessKeyStatus.REVOKED

    def test_restore_active_and_revoked_preserves_all_fields(self) -> None:
        """Оба допустимых состояния восстанавливаются с исходными ID и датами."""
        for status, revoked_at in (
            (AccessKeyStatus.ACTIVE, None),
            (AccessKeyStatus.REVOKED, FINISHED),
        ):
            values = dict(
                identifier=FeedAccessKeyIdVO(uuid4()),
                feed_id=FeedIdVO(uuid4()),
                token_hash=AccessTokenHashVO(bytes(range(32))),
                status=status,
                created_at=NOW,
                revoked_at=revoked_at,
                name=AccessKeyNameVO("Площадка"),
                expires_at=FINISHED,
            )
            self.assertEqual(
                properties(FeedAccessKey.restore(**values)), restored_properties(values)
            )

    def test_digest_requires_immutable_sha256_bytes(self) -> None:
        """Пустые, неверной длины и изменяемые значения не принимаются как digest."""
        for value in (
            None,
            "",
            "a" * 64,
            b"",
            b"a" * 31,
            b"a" * 33,
            bytearray(32),
            memoryview(bytes(32)),
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidAccessKeyValueError),
            ):
                AccessTokenHashVO(value)

    def test_restore_rejects_inconsistent_state_and_types(self) -> None:
        """Активный ключ не имеет отзыва; отозванный требует корректную дату."""
        values = dict(
            identifier=FeedAccessKeyIdVO(uuid4()),
            feed_id=FeedIdVO(uuid4()),
            token_hash=AccessTokenHashVO(b"h" * 32),
            status=AccessKeyStatus.ACTIVE,
            created_at=NOW,
            revoked_at=None,
            name=AccessKeyNameVO("Площадка"),
            expires_at=None,
        )
        for changes in (
            {"status": AccessKeyStatus.REVOKED},
            {"revoked_at": FINISHED},
            {"status": "ACTIVE"},
            {"identifier": FeedIdVO(uuid4())},
            {"feed_id": EntityIdVO(uuid4())},
            {"token_hash": b"h" * 32},
            {"created_at": NOW.replace(tzinfo=None)},
            {"status": AccessKeyStatus.REVOKED, "revoked_at": NOW.replace(tzinfo=None)},
            {
                "status": AccessKeyStatus.REVOKED,
                "revoked_at": NOW - timedelta(seconds=1),
            },
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidAccessKeyValueError),
            ):
                FeedAccessKey.restore(**(values | changes))
        with self.assertRaises(InvalidAccessKeyValueError):
            FeedAccessKey.create(
                identifier=values["identifier"],
                feed_id=values["feed_id"],
                token_hash=values["token_hash"],
                name=values["name"],
                now="now",
            )


if __name__ == "__main__":
    unittest.main()
