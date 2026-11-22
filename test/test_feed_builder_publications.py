"""Участие выбранных позиций: Domain и атомарное Application-поведение."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from unittest import TestCase, IsolatedAsyncioTestCase
from unittest.mock import Mock, AsyncMock
from uuid import uuid4
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.feed_builder.domain.publication.aggregate import FeedPublication
from src.modules.feed_builder.domain.publication.enum.publication_status import (
    PublicationStatus as S,
)
from src.modules.feed_builder.domain.publication.error import (
    PublicationTransitionError,
    InvalidPublicationValueError,
    PublicationVersionConflictError,
)
from src.modules.feed_builder.domain.publication.value_object.feed_publication_id import (
    FeedPublicationIdVO,
)
from src.modules.feed_builder.domain.publication.value_object.feed_publication_version import (
    FeedPublicationVersionVO,
)
from src.modules.feed_builder.domain.publication.value_object.catalog_product_reference import (
    CatalogProductReferenceVO,
)
from src.modules.feed_builder.domain.publication.value_object.field_override import (
    FieldOverrideVO,
)
from src.modules.feed_builder.domain.feed.value_object.field_id import FieldIdVO
from src.modules.feed_builder.domain.feed.value_object.price_amount import PriceAmountVO
from src.modules.feed_builder.domain.feed.error import (
    FeedArchivedError,
    FeedVersionConflictError,
)
from src.modules.feed_builder.application.publication.command.add_catalog_items.command import (
    AddCatalogItemsCommand,
)
from src.modules.feed_builder.application.publication.command.add_catalog_items.handler import (
    AddCatalogItemsHandler,
)
from src.modules.feed_builder.application.publication.port.catalog_subjects import (
    PublicationCatalogSubject,
    PublicationSourceNotFoundError,
)
from src.modules.feed_builder.infrastructure.publication.persistence.mapper import (
    FeedPublicationMapper,
)
from test.test_feed_builder_domain import feed, NOW


def publication() -> FeedPublication:
    """Создаёт самостоятельную привязку без случайного I/O."""
    return FeedPublication.create(
        identifier=FeedPublicationIdVO(uuid4()),
        feed_id=feed().id,
        product_reference=CatalogProductReferenceVO(EntityIdVO(uuid4())),
        now=NOW,
    )


class PublicationBehaviorTests(TestCase):
    """Проверяет неизменяемые переходы и сохранность исходных данных."""

    def test_lifecycle_identity_overrides_version_and_noop(self) -> None:
        """Переходы увеличивают версию ровно один раз и сохраняют ручные значения."""
        original = replace(
            publication(),
            overrides=(
                FieldOverrideVO(
                    FieldIdVO(uuid4()), PriceAmountVO(Decimal("123.4567890123456789"))
                ),
                FieldOverrideVO(FieldIdVO(uuid4()), None),
            ),
        )
        current = original
        for method, status in [
            ("pause", S.PAUSED),
            ("enable", S.ENABLED),
            ("archive", S.ARCHIVED),
            ("restore_participation", S.ENABLED),
        ]:
            before = current
            current = getattr(current, method)(
                now=NOW + timedelta(minutes=current.version.value)
            )
            self.assertEqual(current.status, status)
            self.assertEqual(current.version.value, before.version.value + 1)
            self.assertEqual(current.product_reference, original.product_reference)
            self.assertEqual(current.overrides, original.overrides)
            self.assertEqual(current.created_at, NOW)
            self.assertIs(getattr(current, method)(now=current.updated_at), current)
        self.assertEqual(original.version.value, 1)
        row = FeedPublicationMapper.to_insert_values(current)
        self.assertEqual(FeedPublicationMapper.to_domain(row), current)
        self.assertEqual(
            row["overrides"][str(original.overrides[0].field_id.uuid)]["value"],
            {"amount": "123.4567890123456789"},
        )

    def test_invalid_transitions_and_dates_leave_original_unchanged(self) -> None:
        """Ошибки не оставляют частичного перехода или новой версии."""
        original = publication().archive(now=NOW)
        for method in ("pause", "enable"):
            with self.assertRaises(PublicationTransitionError):
                getattr(original, method)(now=NOW)
        with self.assertRaises(PublicationTransitionError):
            publication().pause(now=NOW).restore_participation(now=NOW)
        for now in (NOW - timedelta(seconds=1), NOW.replace(tzinfo=None)):
            with self.assertRaises(InvalidPublicationValueError):
                original.restore_participation(now=now)
        self.assertEqual(original.version.value, 2)
        for value in (0, -1, True, "1", 2**63):
            with self.assertRaises(InvalidPublicationValueError):
                FeedPublicationVersionVO(value)


class AddPublicationApplicationTests(IsolatedAsyncioTestCase):
    """Проверяет весь пакет до записи и отсутствие изменений Feed."""

    async def asyncSetUp(self) -> None:
        """Собирает необходимые порты и постоянные часы."""
        self.feed = feed()
        self.feeds = Mock(get_for_update=AsyncMock(return_value=self.feed))
        self.publications = Mock(find=AsyncMock(return_value=()), add_many=AsyncMock())
        self.reference = CatalogProductReferenceVO(EntityIdVO(uuid4()))
        self.catalog = Mock(
            read_many=AsyncMock(
                return_value=(
                    PublicationCatalogSubject(
                        self.reference, "simple", None, None, None, True
                    ),
                )
            )
        )
        self.handler = AddCatalogItemsHandler(
            self.feeds,
            self.publications,
            self.catalog,
            Mock(now=lambda: NOW),
            Mock(new=uuid4),
        )

    async def test_deduplicates_preserves_existing_paused_and_archived(self) -> None:
        """Повтор запроса возвращает прежний ID и не возобновляет участие автоматически."""
        query = AddCatalogItemsCommand(
            self.feed.id, 1, (self.reference, self.reference)
        )
        created = await self.handler.execute(query)
        self.assertEqual(len(created.items), 1)
        self.assertEqual(created.items[0].outcome, "CREATED")
        original = self.publications.add_many.call_args.args[0][0]
        self.publications.add_many.reset_mock()
        for status in (S.PAUSED, S.ARCHIVED):
            self.publications.find.return_value = (replace(original, status=status),)
            result = await self.handler.execute(query)
            self.assertEqual(result.items[0].id, original.id.uuid)
            self.assertEqual(result.items[0].status, status.value)
            self.assertEqual(result.items[0].outcome, "EXISTING")
        self.assertEqual(self.feed.version.value, 1)

    async def test_one_invalid_reference_rejects_whole_package_before_write(
        self,
    ) -> None:
        """Не записывает корректную часть пакета при неверной второй ссылке."""
        with self.assertRaises(PublicationSourceNotFoundError):
            await self.handler.execute(
                AddCatalogItemsCommand(
                    self.feed.id,
                    1,
                    (self.reference, CatalogProductReferenceVO(EntityIdVO(uuid4()))),
                )
            )
        self.publications.add_many.assert_not_awaited()
        self.publications.find.assert_not_awaited()

    async def test_feed_conflict_archive_and_limits_stop_before_catalog(self) -> None:
        """Не читает Catalog после отказа по контексту или размеру пакета."""
        with self.assertRaises(FeedVersionConflictError):
            await self.handler.execute(
                AddCatalogItemsCommand(self.feed.id, 2, (self.reference,))
            )
        self.feeds.get_for_update.return_value = self.feed.archive(now=NOW)
        with self.assertRaises(FeedArchivedError):
            await self.handler.execute(
                AddCatalogItemsCommand(self.feed.id, 2, (self.reference,))
            )
        for refs in ((), (self.reference,) * 101):
            with self.assertRaises(InvalidPublicationValueError):
                await self.handler.execute(
                    AddCatalogItemsCommand(self.feed.id, 1, refs)
                )
        self.catalog.read_many.assert_not_awaited()
