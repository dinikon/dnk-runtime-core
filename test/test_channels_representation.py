"""Подготовка контента, границы Catalog и конкретный контракт preview."""

import ast
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

from src.modules.catalog.application.catalog_item.bindings_facade import (
    CatalogBindingsFacade,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_item.dto import (
    CatalogItemDetailsGalleryDTO,
    CatalogItemDetailsImageDTO,
    CatalogItemSourcesDTO,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_product_snapshot.dto import (
    GetCatalogProductSnapshotResultDTO,
)
from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.query_mapper import (
    CatalogItemQueryMapper,
)
from src.modules.channels.application.channel.port.query_repository import (
    ChannelQueryRepository,
    ChannelReadRow,
    ConnectionConfigReadRow,
    VerificationReadRow,
)
from src.modules.channels.application.error import ChannelInputError
from src.modules.channels.application.product_representation.contracts import (
    RepresentationBindingSource,
)
from src.modules.channels.application.product_representation.port.query_repository import (
    RepresentationQueryRepositoryProtocol,
)
from src.modules.channels.application.product_representation.query.preview_representation.handler import (
    PreviewRepresentationHandler,
)
from src.modules.channels.application.product_representation.query.preview_representation.query import (
    PreviewRepresentationQuery,
)
from src.modules.channels.application.product_representation.service.builder import (
    RepresentationBuilder,
)
from src.modules.channels.domain.catalog_binding.entity import CatalogBindingItem
from src.modules.channels.domain.catalog_binding.error import CatalogBindingError
from src.modules.channels.domain.catalog_binding.value_object import (
    BindingClaim,
    BindingMode,
    PublicationNode,
)
from src.modules.channels.domain.channel.enum.verification_status import (
    VerificationStatus,
)
from src.modules.channels.domain.channel.error import ChannelNotFoundError
from src.modules.channels.domain.product_representation.policy import (
    RepresentationPolicy,
)
from src.modules.channels.domain.product_representation.value_object import (
    CatalogContentSnapshot,
    ContentOrigin,
    ContentOrigins,
    ContentTargetRole,
    FieldOrigin,
    LocalizedContent,
    PublicationContentSnapshot,
    RepresentationPreparation,
)
from src.modules.channels.infrastructure.product_representation.catalog import (
    RepresentationCatalogGateway,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


def identifier() -> EntityIdVO:
    """Создаёт независимый ID тестового объекта."""
    return EntityIdVO(uuid4())


def content(position_id: EntityIdVO, kind: str = "simple") -> CatalogContentSnapshot:
    """Создаёт собственный контент с явной очисткой описания и галереи."""
    own = FieldOrigin(ContentOrigin.CATALOG, position_id)
    return CatalogContentSnapshot(
        position_id,
        kind,
        (LocalizedContent("uk", "Назва", "", (), ContentOrigins(own, own, own)),),
    )


def pair(left: EntityIdVO, right: EntityIdVO) -> CatalogBindingItem:
    """Создаёт стабильную пару группы."""
    return CatalogBindingItem.create(
        identifier=identifier(), catalog_position_id=left, publication_id=right
    )


def publication(
    key: EntityIdVO, kind: str = "simple", parent: EntityIdVO | None = None
) -> PublicationContentSnapshot:
    """Создаёт только структурный снимок внешней цели."""
    return PublicationContentSnapshot(
        PublicationNode(key, kind, parent), str(key), False
    )


class RepresentationPolicyTests(TestCase):
    """Проверяет все режимы, частичные семьи и блокировки без инфраструктуры."""

    def setUp(self) -> None:
        """Создаёт корни и две потенциальные пары."""
        self.group, self.root, self.left, self.right = (identifier() for _ in range(4))
        self.pub, self.child, self.second = (identifier() for _ in range(3))

    def prepare(self, **changes: object) -> RepresentationPreparation:
        """Запускает политику с исходным простым сопоставлением."""
        values = {
            "group_id": self.group,
            "platform": "prom",
            "mode": BindingMode.SIMPLE_TO_SIMPLE,
            "catalog_root_id": self.root,
            "catalog_root": content(self.root),
            "catalog_positions": (content(self.root),),
            "publication_root_id": self.pub,
            "items": (pair(self.root, self.pub),),
            "publications": (publication(self.pub),),
            "claims": (),
        }
        return RepresentationPolicy().prepare(**(values | changes))

    def test_simple_all_platforms_preserves_empty_values_and_pair_id(self) -> None:
        """Пустая галерея/описание не превращаются в отсутствие поля."""
        binding = pair(self.root, self.pub)
        for platform in ("prom", "rozetka", "woocommerce"):
            with self.subTest(platform=platform):
                result = self.prepare(platform=platform, items=(binding,))
                self.assertEqual(result.assessment.state, "linked")
                target = result.targets[0]
                self.assertTrue(target.ready)
                self.assertEqual(target.binding_item_id, binding.id)
                self.assertEqual(target.role, ContentTargetRole.POSITION)
                self.assertEqual(target.content[0].body, "")
                self.assertEqual(target.content[0].gallery, ())
                self.assertEqual(
                    target.content[0].origins.title.catalog_position_id, self.root
                )

    def test_variable_to_simple_partial_keeps_independent_target_ready(self) -> None:
        """Несопоставленная позиция не запрещает подготовку независимой пары."""
        for platform in ("prom", "rozetka", "woocommerce"):
            result = self.prepare(
                platform=platform,
                mode=BindingMode.VARIABLE_TO_SIMPLE,
                catalog_root=content(self.root, "variable"),
                catalog_positions=(
                    content(self.left, "variant"),
                    content(self.right, "variant"),
                ),
                publication_root_id=None,
                items=(pair(self.left, self.pub),),
            )
            self.assertEqual(result.assessment.state, "partial")
            self.assertTrue(result.targets[0].ready)
            self.assertEqual(result.targets[0].catalog_position_id, self.left)

    def test_prom_family_keeps_base_product_as_sellable_pair(self) -> None:
        """Основной товар Prom не подменяется общим контейнером Catalog."""
        result = self.prepare(
            mode=BindingMode.VARIABLE_TO_VARIABLE,
            catalog_root=content(self.root, "variable"),
            catalog_positions=(
                content(self.left, "variant"),
                content(self.right, "variant"),
            ),
            items=(pair(self.left, self.pub), pair(self.right, self.child)),
            publications=(
                publication(self.pub),
                publication(self.child, "variant", self.pub),
            ),
        )
        self.assertEqual(result.assessment.state, "linked")
        self.assertEqual(
            [target.publication_id for target in result.targets], [self.pub, self.child]
        )
        self.assertTrue(all(target.ready for target in result.targets))
        self.assertEqual(result.targets[0].catalog_position_id, self.left)
        self.assertEqual(result.targets[1].parent_publication_id, self.pub)

    def test_woo_container_requires_complete_family(self) -> None:
        """Общий контейнер блокируется при частичной семье, вариация остаётся видимой."""
        values = dict(
            platform="woocommerce",
            mode=BindingMode.VARIABLE_TO_VARIABLE,
            catalog_root=content(self.root, "variable"),
            catalog_positions=(
                content(self.left, "variant"),
                content(self.right, "variant"),
            ),
            publications=(
                publication(self.pub, "variable"),
                publication(self.child, "variant", self.pub),
                publication(self.second, "variant", self.pub),
            ),
        )
        partial = self.prepare(**values, items=(pair(self.left, self.child),))
        container, variation = partial.targets
        self.assertEqual(container.role, ContentTargetRole.CONTAINER)
        self.assertEqual(container.catalog_position_id, self.root)
        self.assertIsNone(container.binding_item_id)
        self.assertIn(
            "representation_family_incomplete",
            [issue.code for issue in container.issues],
        )
        self.assertTrue(variation.ready)
        complete = self.prepare(
            **values, items=(pair(self.left, self.child), pair(self.right, self.second))
        )
        self.assertEqual(complete.assessment.state, "linked")
        self.assertTrue(all(target.ready for target in complete.targets))

    def test_conflicts_missing_sources_and_stale_observation_remain_visible(
        self,
    ) -> None:
        """Ошибки не заменяют preview исключением и не скрывают исходные пары."""
        for changes, code in (
            (
                {"catalog_root": None, "catalog_positions": ()},
                "binding_catalog_missing",
            ),
            ({"publications": ()}, "representation_publication_missing"),
            (
                {"claims": (BindingClaim(identifier(), self.pub),)},
                "binding_publication_occupied",
            ),
            (
                {"publications": (replace(publication(self.pub), stale=True),)},
                "representation_publication_stale",
            ),
            (
                {"mode": BindingMode.VARIABLE_TO_VARIABLE, "platform": "rozetka"},
                "binding_variable_structure_invalid",
            ),
        ):
            with self.subTest(code=code):
                result = self.prepare(**changes)
                self.assertEqual(len(result.targets), 1)
                self.assertFalse(result.targets[0].ready)
                self.assertIn(code, [issue.code for issue in result.targets[0].issues])

    def test_missing_locale_title_has_no_cross_locale_fallback(self) -> None:
        """Диагностика указывает точное поле/локаль; пустой body остаётся допустимым."""
        root = content(self.root)
        missing = FieldOrigin(ContentOrigin.MISSING, None)
        root = replace(
            root,
            content=root.content
            + (
                LocalizedContent(
                    "ru", None, None, None, ContentOrigins(missing, missing, missing)
                ),
            ),
        )
        result = self.prepare(catalog_root=root, catalog_positions=(root,))
        target = result.targets[0]
        self.assertEqual(len(target.content), 2)
        self.assertIsNone(target.content[1].title)
        self.assertEqual(
            [
                (issue.code, issue.field, issue.locale, issue.publication_id)
                for issue in target.issues
            ],
            [("representation_title_missing", "title", "ru", self.pub)],
        )


class RepresentationCatalogGatewayTests(IsolatedAsyncioTestCase):
    """Проверяет перевод публичного Catalog DTO, порядок media и независимость снимка."""

    async def test_multilocale_mapping_preserves_sources_and_missing_vs_empty(
        self,
    ) -> None:
        """Не читает ORM Catalog и не выдаёт Console URL в экспортируемом контенте."""
        now = datetime.now(UTC)
        root, child = uuid4(), uuid4()
        item = CatalogItem.create(
            CatalogItemIdVO(root), identifier(), now, identifier()
        )
        details = CatalogItemQueryMapper.details(item.snapshot(), "uk", now)
        image_a, image_b, file_a, file_b = (uuid4() for _ in range(4))
        images = (
            CatalogItemDetailsImageDTO(image_a, file_a, 0, "A", "First"),
            CatalogItemDetailsImageDTO(image_b, file_b, 1, "B", "Main"),
        )
        parent = replace(
            details,
            kind="variable",
            effective_content={"title": "Батьківська назва", "body": "Parent body"},
        )
        variant = replace(
            details,
            id=child,
            kind="variant",
            parent_id=root,
            effective_content={"title": "Батьківська назва", "body": ""},
            effective_gallery=CatalogItemDetailsGalleryDTO(images, image_b),
            sources=CatalogItemSourcesDTO(root, child, root, None, None, child),
        )
        ru = replace(
            variant,
            effective_content=None,
            effective_gallery=CatalogItemDetailsGalleryDTO((), None),
            sources=CatalogItemSourcesDTO(None, None, child, None, None, child),
        )
        facade = Mock(spec=CatalogBindingsFacade)
        facade.families_for_locales = AsyncMock(
            return_value=(
                GetCatalogProductSnapshotResultDTO(parent, (variant,), "uk", now),
                GetCatalogProductSnapshotResultDTO(
                    replace(parent, effective_content=None), (ru,), "ru", now
                ),
            )
        )
        family = await RepresentationCatalogGateway(facade).family(
            root_id=root, locales=("uk", "ru"), as_of=now
        )
        uk_content, ru_content = family.positions[0].content
        self.assertEqual(uk_content.origins.title.kind, ContentOrigin.CATALOG_PARENT)
        self.assertEqual(uk_content.origins.body.kind, ContentOrigin.CATALOG)
        self.assertEqual(uk_content.origins.title.catalog_position_id.uuid, root)
        self.assertEqual(
            [image.file_id.uuid for image in uk_content.gallery], [file_b, file_a]
        )
        self.assertEqual(uk_content.body, "")
        self.assertIsNone(ru_content.title)
        self.assertEqual(ru_content.gallery, ())
        variant.effective_content["title"] = "Changed after read"
        self.assertEqual(uk_content.title, "Батьківська назва")
        facade.families_for_locales.assert_awaited_once_with(
            identifiers=(root,), locales=("uk", "ru"), as_of=now
        )

    async def test_catalog_public_batch_uses_same_time_for_every_locale(self) -> None:
        """Все локали читаются через один порт внешнего UoW с общим as_of."""
        now = datetime.now(UTC)
        root = uuid4()
        repository = Mock()
        repository.snapshots = AsyncMock(return_value=())
        facade = CatalogBindingsFacade(repository, Mock())
        self.assertEqual(
            await facade.families_for_locales(
                identifiers=(root,), locales=("uk", "ru"), as_of=now
            ),
            (),
        )
        self.assertEqual(
            [call.args for call in repository.snapshots.await_args_list],
            [((root,), "uk", now), ((root,), "ru", now)],
        )


class PreviewRepresentationHandlerTests(IsolatedAsyncioTestCase):
    """Проверяет границы запроса, выбор локалей и отсутствие обращения к credentials."""

    async def asyncSetUp(self) -> None:
        """Собирает handler на портах и настоящем реестре локальной валидации."""
        self.now = datetime.now(UTC)
        self.channel, self.group = uuid4(), uuid4()
        self.channels = Mock(spec=ChannelQueryRepository)
        self.channels.get = AsyncMock(
            return_value=ChannelReadRow(
                self.channel,
                "Prom",
                "prom",
                1,
                ConnectionConfigReadRow(1, "https://my.prom.ua", {}),
                1,
                None,
                VerificationReadRow(uuid4(), 1, VerificationStatus.PENDING, None, None),
                self.now,
                self.now,
            )
        )
        self.read = Mock(spec=RepresentationQueryRepositoryProtocol)
        self.read.binding = AsyncMock(
            return_value=RepresentationBindingSource(
                self.group,
                uuid4(),
                uuid4(),
                BindingMode.SIMPLE_TO_SIMPLE,
                uuid4(),
                1,
                (),
            )
        )
        self.builder = Mock(spec=RepresentationBuilder)
        self.builder.build = AsyncMock(return_value="prepared-result")
        self.clock = Mock()
        self.clock.now.return_value = self.now
        self.http = Mock()
        self.handler = PreviewRepresentationHandler(
            channels=self.channels,
            representations=self.read,
            platforms=InstalledPlatforms(self.http),
            builder=self.builder,
            clock=self.clock,
        )

    async def test_uses_configured_locales_and_does_not_require_verified_connection(
        self,
    ) -> None:
        """Preview можно открыть до проверки; ready не является разрешением отправки."""
        result = await self.handler.execute(
            PreviewRepresentationQuery(self.channel, self.group)
        )
        self.assertEqual(result.representation, "prepared-result")
        self.assertEqual(self.builder.build.call_args.kwargs["locales"], ("uk", "ru"))
        self.assertEqual(self.builder.build.call_args.kwargs["as_of"], self.now)
        self.http.request.assert_not_called()

    async def test_invalid_locale_selection_is_rejected_before_build(self) -> None:
        """Пустой список, дубликаты и ненастроенный язык не запускают чтение Catalog."""
        for locales in ((), ("uk", "uk"), ("en",)):
            with self.assertRaises(ChannelInputError) as caught:
                await self.handler.execute(
                    PreviewRepresentationQuery(self.channel, self.group, locales)
                )
            self.assertEqual(caught.exception.code, "representation_locales_invalid")
        self.builder.build.assert_not_awaited()

    async def test_missing_channel_or_foreign_group_is_not_previewed(self) -> None:
        """Отсутствие канала и принадлежность группы проверяются до сборки контента."""
        self.read.binding.return_value = None
        with self.assertRaises(CatalogBindingError):
            await self.handler.execute(
                PreviewRepresentationQuery(self.channel, self.group)
            )
        self.channels.get.return_value = None
        with self.assertRaises(ChannelNotFoundError):
            await self.handler.execute(
                PreviewRepresentationQuery(self.channel, self.group)
            )
        self.builder.build.assert_not_awaited()


class RepresentationArchitectureTests(TestCase):
    """Удерживает внутренние слои без зависимостей от ORM, HTTP и моделей платформ."""

    def test_dependencies_point_inward_and_packages_have_no_reexports(self) -> None:
        """Вычисляемый срез не создаёт репозитории агрегатов или лишнее хранение."""
        root = Path(__file__).resolve().parents[1] / "src/modules/channels"
        for layer in ("domain", "application"):
            for path in (root / layer / "product_representation").rglob("*.py"):
                for node in ast.walk(ast.parse(path.read_text())):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        self.assertFalse(
                            node.module.startswith(
                                (
                                    "fastapi",
                                    "pydantic",
                                    "sqlalchemy",
                                    "src.modules.channels.infrastructure",
                                    "src.modules.channels.presentation",
                                    "src.modules.catalog",
                                )
                            ),
                            str(path),
                        )
                        if layer == "domain":
                            self.assertFalse(
                                node.module.startswith(
                                    "src.modules.channels.application"
                                ),
                                str(path),
                            )
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self.assertIsNotNone(node.returns, f"{path}: {node.name}")
                        self.assertNotEqual(node.name, "__post_init__")
        for path in root.glob("*/product_representation/**/__init__.py"):
            self.assertEqual(path.read_text(), "", str(path))
