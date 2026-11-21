"""Состояния публикаций, генераций и ключей доступа без I/O и переходов поведения."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
from uuid import uuid4
import unittest

from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.money import MoneyVO
from src.modules.feed_builder.domain.feed.value_object.price_amount import PriceAmountVO
from test.test_feed_builder_domain import text_field, money_field
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.value_object.field_id import FieldIdVO
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.domain.feed.value_object.feed_export_settings import (
    FeedExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.csv_export_settings import (
    CsvExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.value_object.xml_export_settings import (
    XmlExportSettingsVO,
)
from src.modules.feed_builder.domain.feed.enum.export_format import ExportFormat
from src.modules.feed_builder.domain.feed.enum.feed_product_mode import FeedProductMode
from src.modules.feed_builder.domain.feed.error import (
    DuplicateFieldIdentifierError,
    InvalidFieldDefinitionError,
)
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
from src.modules.feed_builder.domain.access_key.value_object.feed_access_key_id import (
    FeedAccessKeyIdVO,
)
from src.modules.feed_builder.domain.access_key.value_object.access_token_hash import (
    AccessTokenHashVO,
)
from src.modules.feed_builder.domain.generation.aggregate import FeedGeneration
from src.modules.feed_builder.domain.generation.entity.feed_artifact import FeedArtifact
from src.modules.feed_builder.domain.generation.enum.generation_status import (
    GenerationStatus,
)
from src.modules.feed_builder.domain.generation.error import InvalidGenerationValueError
from src.modules.feed_builder.domain.generation.value_object.feed_generation_id import (
    FeedGenerationIdVO,
)
from src.modules.feed_builder.domain.generation.value_object.feed_artifact_id import (
    FeedArtifactIdVO,
)
from src.modules.feed_builder.domain.generation.value_object.generation_sequence import (
    GenerationSequenceVO,
)
from src.modules.feed_builder.domain.generation.value_object.calculation_engine_version import (
    CalculationEngineVersionVO,
)
from src.modules.feed_builder.domain.generation.value_object.generation_definition_snapshot import (
    GenerationDefinitionSnapshotVO,
)
from src.modules.feed_builder.domain.generation.value_object.generation_calculation_context import (
    GenerationCalculationContextVO,
)
from src.modules.feed_builder.domain.generation.value_object.generation_counts import (
    GenerationCountsVO,
)
from src.modules.feed_builder.domain.generation.value_object.generation_failure import (
    GenerationFailureVO,
)
from src.modules.feed_builder.domain.generation.value_object.generation_attempt import (
    GenerationAttemptVO,
)
from src.modules.feed_builder.domain.generation.value_object.generation_attempt_token import (
    GenerationAttemptTokenVO,
)
from src.modules.feed_builder.domain.generation.value_object.artifact_checksum import (
    ArtifactChecksumVO,
)
from src.modules.feed_builder.domain.generation.value_object.artifact_content_type import (
    ArtifactContentTypeVO,
)
from src.modules.feed_builder.domain.generation.value_object.artifact_storage_key import (
    ArtifactStorageKeyVO,
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


def snapshot(*, xml: bool = False) -> GenerationDefinitionSnapshotVO:
    """Создаёт снимок пользовательской схемы и одного явно выбранного формата."""
    return GenerationDefinitionSnapshotVO(
        schema=FeedSchemaVO((text_field(), money_field())),
        export_settings=FeedExportSettingsVO(
            format_settings=(
                XmlExportSettingsVO() if xml else CsvExportSettingsVO(delimiter=";")
            )
        ),
        calculation_engine_version=CalculationEngineVersionVO(1),
    )


def artifact(*, xml: bool = False) -> FeedArtifact:
    """Создаёт метаданные файла без записи в хранилище."""
    return FeedArtifact.create(
        identifier=FeedArtifactIdVO(uuid4()),
        format=ExportFormat.XML if xml else ExportFormat.CSV,
        storage_key=ArtifactStorageKeyVO(
            "feeds/result.xml" if xml else "feeds/result.csv"
        ),
        content_type=ArtifactContentTypeVO("application/xml" if xml else "text/csv"),
        checksum=ArtifactChecksumVO("a" * 64),
        size_bytes=42,
        now=FINISHED,
    )


def pending_values() -> dict[str, object]:
    """Задаёт независимые свойства начального задания для тестов восстановления."""
    return dict(
        identifier=FeedGenerationIdVO(uuid4()),
        feed_id=FeedIdVO(uuid4()),
        request_sequence=GenerationSequenceVO(7),
        definition_snapshot=snapshot(),
        status=GenerationStatus.PENDING,
        calculation_context=None,
        attempt_count=0,
        current_attempt=None,
        counts=GenerationCountsVO(),
        failure=None,
        artifact=None,
        requested_at=NOW,
        started_at=None,
        finished_at=None,
    )


def running_values() -> dict[str, object]:
    """Задаёт вторую попытку с фиксированным контекстом и частичным прогрессом."""
    return pending_values() | dict(
        status=GenerationStatus.RUNNING,
        attempt_count=2,
        current_attempt=GenerationAttemptVO(
            number=2,
            token=GenerationAttemptTokenVO(uuid4()),
            claimed_at=STARTED + timedelta(seconds=10),
            lease_until=FINISHED,
        ),
        started_at=STARTED,
        calculation_context=GenerationCalculationContextVO(STARTED),
        counts=GenerationCountsVO(5, 2, 1),
    )


def succeeded_values(*, xml: bool = False) -> dict[str, object]:
    """Задаёт завершённую STRICT-генерацию с единственным файлом."""
    return running_values() | dict(
        definition_snapshot=snapshot(xml=xml),
        status=GenerationStatus.SUCCEEDED,
        current_attempt=None,
        counts=GenerationCountsVO(5, 5, 0),
        artifact=artifact(xml=xml),
        finished_at=FINISHED,
    )


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
            12,
            Decimal("12"),
            True,
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
            identifier=identifier, feed_id=feed_id, token_hash=digest, now=NOW
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
                now="now",
            )


class FeedGenerationDomainTests(unittest.TestCase):
    """Проверяет снимок, попытки, счётчики и единственный итоговый артефакт."""

    def test_create_pending_sets_every_field_for_csv_and_xml(self) -> None:
        """Новая генерация фиксирует один формат и не содержит выполненной работы."""
        for xml in (False, True):
            values = pending_values() | {"definition_snapshot": snapshot(xml=xml)}
            result = FeedGeneration.create(
                identifier=values["identifier"],
                feed_id=values["feed_id"],
                request_sequence=values["request_sequence"],
                definition_snapshot=values["definition_snapshot"],
                now=NOW,
            )
            self.assertEqual(properties(result), restored_properties(values))
            self.assertIs(
                result.definition_snapshot.export_settings.product_mode,
                FeedProductMode.VARIABLE_TO_SINGLE,
            )

    def test_snapshot_preserves_optional_currency_without_fx_for_both_factories(
        self,
    ) -> None:
        """Снимок задания сохраняет None/код без валюты источника или конвертера."""
        for currency in (None, UAH, CurrencyVO("USD")):
            definition = snapshot()
            first, price = definition.schema.fields
            price = replace(
                price, type_definition=replace(price.type_definition, currency=currency)
            )
            definition = replace(definition, schema=FeedSchemaVO((first, price)))
            created = FeedGeneration.create(
                identifier=FeedGenerationIdVO(uuid4()),
                feed_id=FeedIdVO(uuid4()),
                request_sequence=GenerationSequenceVO(1),
                definition_snapshot=definition,
                now=NOW,
            )
            values = properties(created)
            values["identifier"] = values.pop("id")
            restored = FeedGeneration.restore(**values)
            self.assertEqual(restored, created)
            self.assertEqual(
                restored.definition_snapshot.schema.fields[1].type_definition.currency,
                currency,
            )

    def test_restore_all_valid_states_preserves_every_field(self) -> None:
        """Восстановление сохраняет прогресс, контекст и причину ошибки без переходов."""
        failed = running_values() | dict(
            status=GenerationStatus.FAILED,
            current_attempt=None,
            failure=GenerationFailureVO(
                "invalid_price", "Некорректное денежное значение"
            ),
            finished_at=FINISHED,
        )
        failed_before_claim = pending_values() | dict(
            status=GenerationStatus.FAILED,
            failure=GenerationFailureVO(
                "dependency_unavailable", "Источник недоступен"
            ),
            finished_at=FINISHED,
        )
        for values in (
            pending_values(),
            running_values(),
            succeeded_values(),
            succeeded_values(xml=True),
            failed,
            failed_before_claim,
        ):
            with self.subTest(status=values["status"]):
                self.assertEqual(
                    properties(FeedGeneration.restore(**values)),
                    restored_properties(values),
                )

    def test_pending_cannot_contain_work_or_results(self) -> None:
        """PENDING не допускает контекст, прогресс, попытку, ошибку или файл."""
        values = pending_values()
        for changes in (
            {"counts": GenerationCountsVO(1)},
            {"attempt_count": 1},
            {"started_at": STARTED},
            {"finished_at": FINISHED},
            {"calculation_context": GenerationCalculationContextVO(STARTED)},
            {"current_attempt": running_values()["current_attempt"]},
            {"failure": GenerationFailureVO("failed", "Ошибка")},
            {"artifact": artifact()},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidGenerationValueError),
            ):
                FeedGeneration.restore(**(values | changes))

    def test_running_requires_matching_attempt_and_unfinished_state(self) -> None:
        """Токен относится к текущей пронумерованной попытке, не к другому запуску."""
        values = running_values()
        attempt = values["current_attempt"]
        for changes in (
            {"current_attempt": None},
            {"attempt_count": 1},
            {"current_attempt": replace(attempt, claimed_at=NOW)},
            {"started_at": None},
            {"finished_at": FINISHED},
            {"failure": GenerationFailureVO("failed", "Ошибка")},
            {"artifact": artifact()},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidGenerationValueError),
            ):
                FeedGeneration.restore(**(values | changes))
        with self.assertRaises(InvalidGenerationValueError):
            FeedGeneration.restore(**(values | {"calculation_context": None}))
        without_context = FeedGeneration.restore(
            **(
                values
                | {
                    "calculation_context": None,
                    "counts": GenerationCountsVO(5),
                }
            )
        )
        self.assertIsNone(without_context.calculation_context)

    def test_restore_allows_expired_lease_without_consulting_clock(self) -> None:
        """Историческое RUNNING можно восстановить после истечения захвата."""
        values = running_values()
        self.assertEqual(
            FeedGeneration.restore(**values).current_attempt, values["current_attempt"]
        )

    def test_succeeded_requires_complete_strict_result(self) -> None:
        """Успех требует контекст, файл и отсутствие отклонённых STRICT-позиций."""
        values = succeeded_values()
        for changes in (
            {"artifact": None},
            {"calculation_context": None},
            {"finished_at": None},
            {"counts": GenerationCountsVO(5, 4, 0)},
            {"counts": GenerationCountsVO(5, 4, 1)},
            {"current_attempt": running_values()["current_attempt"]},
            {"failure": GenerationFailureVO("failed", "Ошибка")},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidGenerationValueError),
            ):
                FeedGeneration.restore(**(values | changes))
        empty_result = FeedGeneration.restore(
            **(
                values
                | {
                    "counts": GenerationCountsVO(),
                    "artifact": replace(artifact(), size_bytes=0),
                }
            )
        )
        self.assertEqual(empty_result.counts.exported_items, 0)

    def test_failed_requires_reason_and_no_artifact(self) -> None:
        """Ошибка хранит частичный прогресс, но не итоговый файл или активную попытку."""
        values = running_values() | dict(
            status=GenerationStatus.FAILED,
            current_attempt=None,
            failure=GenerationFailureVO("invalid_price", "Ошибка цены"),
            finished_at=FINISHED,
        )
        for changes in (
            {"failure": None},
            {"finished_at": None},
            {"artifact": artifact()},
            {"current_attempt": running_values()["current_attempt"]},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidGenerationValueError),
            ):
                FeedGeneration.restore(**(values | changes))

    def test_generation_checks_artifact_format_and_time(self) -> None:
        """Файл другого формата или вне времени сборки не может стать результатом."""
        values = succeeded_values()
        for result in (
            artifact(xml=True),
            replace(artifact(), created_at=NOW),
            replace(artifact(), created_at=FINISHED + timedelta(seconds=1)),
            replace(artifact(), content_type=ArtifactContentTypeVO("application/xml")),
            replace(artifact(), size_bytes=-1),
        ):
            with (
                self.subTest(artifact=result),
                self.assertRaises(InvalidGenerationValueError),
            ):
                FeedGeneration.restore(**(values | {"artifact": result}))

    def test_generation_validates_snapshot_schema_at_aggregate_boundary(self) -> None:
        """Снимок не обходит уникальность полей и проверки вложенных Entity."""
        field = text_field()
        invalid_schemas = (
            (FeedSchemaVO((field, field)), DuplicateFieldIdentifierError),
            (
                FeedSchemaVO((replace(field, type_definition="string"),)),
                InvalidFieldDefinitionError,
            ),
        )
        for schema, error in invalid_schemas:
            values = pending_values()
            invalid_snapshot = replace(values["definition_snapshot"], schema=schema)
            with self.subTest(schema=schema):
                with self.assertRaises(error):
                    FeedGeneration.restore(
                        **(values | {"definition_snapshot": invalid_snapshot})
                    )
                with self.assertRaises(error):
                    FeedGeneration.create(
                        identifier=values["identifier"],
                        feed_id=values["feed_id"],
                        request_sequence=values["request_sequence"],
                        definition_snapshot=invalid_snapshot,
                        now=NOW,
                    )

    def test_restore_rejects_untyped_generation_properties(self) -> None:
        """Строковые статусы, чужие ID и сырые вложенные структуры отвергаются."""

        class ForeignStatus(StrEnum):
            """Имитирует равную строку из постороннего enum."""

            PENDING = "PENDING"

        values = pending_values()
        for changes in (
            {"identifier": FeedIdVO(uuid4())},
            {"feed_id": EntityIdVO(uuid4())},
            {"request_sequence": 7},
            {"definition_snapshot": {}},
            {"status": "PENDING"},
            {"status": ForeignStatus.PENDING},
            {"attempt_count": True},
            {"attempt_count": -1},
            {"counts": {}},
            {"failure": "failed"},
            {"artifact": []},
            {"calculation_context": {}},
            {"current_attempt": {}},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidGenerationValueError),
            ):
                FeedGeneration.restore(**(values | changes))

    def test_dates_are_aware_and_chronologically_consistent(self) -> None:
        """Начало, контекст, файл и завершение не могут противоречить друг другу."""
        values = succeeded_values()
        for changes in (
            {"requested_at": NOW.replace(tzinfo=None)},
            {"started_at": NOW - timedelta(seconds=1)},
            {"finished_at": NOW},
            {"started_at": STARTED.replace(tzinfo=None)},
            {"finished_at": "later"},
            {"calculation_context": GenerationCalculationContextVO(NOW)},
            {
                "calculation_context": GenerationCalculationContextVO(
                    FINISHED + timedelta(seconds=1)
                )
            },
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidGenerationValueError),
            ):
                FeedGeneration.restore(**(values | changes))
        offset = timezone(timedelta(hours=2))
        values = pending_values() | {"requested_at": NOW.astimezone(offset)}
        self.assertEqual(FeedGeneration.restore(**values).requested_at, NOW)

    def test_context_is_reused_unchanged_between_attempts(self) -> None:
        """Новая попытка сохраняет прежнее as_of без валютного контекста."""
        context = GenerationCalculationContextVO(STARTED)
        values = running_values() | {"calculation_context": context}
        first = FeedGeneration.restore(**values)
        retry = FeedGeneration.restore(
            **(
                values
                | {
                    "attempt_count": 3,
                    "current_attempt": GenerationAttemptVO(
                        3,
                        GenerationAttemptTokenVO(uuid4()),
                        STARTED + timedelta(seconds=20),
                        FINISHED,
                    ),
                }
            )
        )
        self.assertIs(first.calculation_context, retry.calculation_context)
        self.assertEqual(retry.calculation_context.as_of, STARTED)
        self.assertEqual(
            {item.name for item in fields(retry.calculation_context)}, {"as_of"}
        )
        with self.assertRaises(FrozenInstanceError):
            retry.calculation_context.as_of = FINISHED
        with self.assertRaises(FrozenInstanceError):
            retry.definition_snapshot.export_settings.format_settings.delimiter = ","
        with self.assertRaises(FrozenInstanceError):
            retry.status = GenerationStatus.FAILED

    def test_context_only_accepts_explicit_aware_time(self) -> None:
        """Расчётный контекст не принимает курсы или устаревшие FX-настройки."""
        for value in (None, "now", STARTED.replace(tzinfo=None)):
            with (
                self.subTest(value=value),
                self.assertRaises(InvalidGenerationValueError),
            ):
                GenerationCalculationContextVO(value)
        with self.assertRaises(TypeError):
            GenerationCalculationContextVO(STARTED, fx_rate_snapshot=None)

    def test_counts_reject_negative_boolean_and_overcount(self) -> None:
        """Счётчики не допускают bool, отрицательные и учёт сверх выбранных позиций."""
        for counts in (
            (-1, 0, 0),
            (1, -1, 0),
            (1, 0, -1),
            (True, 0, 0),
            (2, 2, 1),
            (1.0, 0, 0),
        ):
            with (
                self.subTest(counts=counts),
                self.assertRaises(InvalidGenerationValueError),
            ):
                GenerationCountsVO(*counts)

    def test_sequence_and_engine_version_require_positive_integers(self) -> None:
        """Технические счётчики не становятся ревизиями схем и исключают bool."""
        for cls in (GenerationSequenceVO, CalculationEngineVersionVO):
            for value in (0, -1, True, 1.0, "1", None):
                with (
                    self.subTest(cls=cls, value=value),
                    self.assertRaises(InvalidGenerationValueError),
                ):
                    cls(value)

    def test_attempt_requires_typed_token_and_positive_lease_interval(self) -> None:
        """Захват содержит явный токен, положительный номер и корректные даты."""
        token = GenerationAttemptTokenVO(uuid4())
        for args in (
            (0, token, STARTED, FINISHED),
            (True, token, STARTED, FINISHED),
            (1, EntityIdVO(uuid4()), STARTED, FINISHED),
            (1, token, STARTED, STARTED),
            (1, token, FINISHED, STARTED),
            (1, token, STARTED.replace(tzinfo=None), FINISHED),
        ):
            with (
                self.subTest(args=args),
                self.assertRaises(InvalidGenerationValueError),
            ):
                GenerationAttemptVO(*args)

    def test_definition_snapshot_requires_explicit_typed_settings(self) -> None:
        """Нельзя передать сырые схему, формат или версию семантики."""
        valid = snapshot()
        for changes in (
            {"schema": {}},
            {"export_settings": None},
            {"export_settings": "csv"},
            {"calculation_engine_version": 1},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidGenerationValueError),
            ):
                replace(valid, **changes)

    def test_failure_uses_bounded_safe_contract(self) -> None:
        """Контракт ограничивает код и описание без помещения исключений в Domain."""
        for code, message in (
            ("", "Ошибка"),
            ("BAD CODE", "Ошибка"),
            ("failed", ""),
            ("failed", "a\nb"),
            ("failed", "a" * 1001),
            ("failed", RuntimeError("error")),
        ):
            with (
                self.subTest(code=code),
                self.assertRaises(InvalidGenerationValueError),
            ):
                GenerationFailureVO(code, message)


class FeedArtifactDomainTests(unittest.TestCase):
    """Проверяет зависимую Entity итогового файла."""

    def test_create_and_restore_preserve_all_fields_for_both_formats(self) -> None:
        """Обе фабрики сохраняют все метаданные с явным соответствием MIME и формата."""
        for xml in (False, True):
            result = artifact(xml=xml)
            expected = properties(result)
            values = expected.copy()
            values["identifier"] = values.pop("id")
            self.assertEqual(properties(FeedArtifact.restore(**values)), expected)
            self.assertEqual(
                result.format, ExportFormat.XML if xml else ExportFormat.CSV
            )
            self.assertEqual(
                result.content_type.value, "application/xml" if xml else "text/csv"
            )
            self.assertEqual(result.size_bytes, 42)
            self.assertEqual(result.created_at, FINISHED)
            with self.assertRaises(FrozenInstanceError):
                result.storage_key = ArtifactStorageKeyVO("other")

    def test_artifact_rejects_invalid_metadata_in_both_factories(self) -> None:
        """Неверные форматы, MIME, размеры и даты не проходят create или restore."""
        values = properties(artifact())
        values["identifier"] = values.pop("id")
        for changes in (
            {"identifier": FeedIdVO(uuid4())},
            {"format": "csv"},
            {"storage_key": "file"},
            {"content_type": "text/csv"},
            {"content_type": ArtifactContentTypeVO("application/xml")},
            {"checksum": "a" * 64},
            {"size_bytes": -1},
            {"size_bytes": True},
            {"created_at": FINISHED.replace(tzinfo=None)},
        ):
            with self.subTest(changes=changes):
                changed = values | changes
                with self.assertRaises(InvalidGenerationValueError):
                    FeedArtifact.restore(**changed)
                changed["now"] = changed.pop("created_at")
                with self.assertRaises(InvalidGenerationValueError):
                    FeedArtifact.create(**changed)

    def test_artifact_value_objects_reject_bad_representations(self) -> None:
        """Ключ, MIME и checksum проверяются до сборки зависимой Entity."""
        for cls, bad_values in (
            (ArtifactStorageKeyVO, (None, "", "a\nb", "a" * 1025)),
            (
                ArtifactContentTypeVO,
                (None, "text/html", "text/csv\r\nX: bad", "text/xml"),
            ),
            (ArtifactChecksumVO, (None, "", "A" * 64, "g" * 64, "a" * 63)),
        ):
            for value in bad_values:
                with (
                    self.subTest(cls=cls, value=value),
                    self.assertRaises(InvalidGenerationValueError),
                ):
                    cls(value)


if __name__ == "__main__":
    unittest.main()
