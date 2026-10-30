"""Реальный HTTP preview на согласованном снимке PostgreSQL без новых таблиц."""

from dataclasses import replace
from datetime import datetime
from unittest import TestLoader, TestSuite
from unittest.mock import patch
from uuid import UUID, uuid4

from sqlalchemy import update

from src.modules.catalog.infrastructure.catalog_item.persistence.query_repository import (
    SqlAlchemyCatalogItemQueryRepository,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_product_snapshot.dto import (
    GetCatalogProductSnapshotResultDTO,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item import (
    CatalogItemModel,
)
from src.modules.channels.infrastructure.persistence.models.catalog_binding_group import (
    CatalogBindingGroupModel,
)
from src.modules.channels.infrastructure.persistence.models.catalog_binding_item import (
    CatalogBindingItemModel,
)
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel,
)
from src.modules.channels.infrastructure.persistence.models.sync_run import SyncRunModel
from src.modules.shared.infrastructure.jobs.scheduled_job_model import ScheduledJobModel
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from test import test_catalog_bindings_postgres as support


class RepresentationPostgresTests(support.CatalogBindingsPostgresTests):
    """Использует готовые fixtures Catalog/публикаций с настоящими UoW и CSRF."""

    async def group(
        self,
        channel: str,
        root: str,
        positions: list[str],
        publications: list[str],
        mode: str = "SIMPLE_TO_SIMPLE",
        publication_root: str | None = None,
    ) -> str:
        """Создаёт сохранённую группу через существующий публичный HTTP-контракт."""
        payload, preview = await self.propose(
            channel, root, positions, publications, mode, publication_root
        )
        body = {key: value for key, value in payload.items() if key != "group_id"} | {
            "catalog_token": preview["catalog_token"],
            "publication_token": preview["publication_token"],
        }
        return (
            await self.call("POST", f"/channels/{channel}/catalog-bindings", body, 201)
        )["id"]

    async def preview(
        self, channel: str, group: str, locales: list[str] | None = None
    ) -> dict:
        """Читает вычисленное представление отдельным POST без записи."""
        body = {"locales": locales} if locales is not None else {}
        return (
            await self.call(
                "POST",
                f"/channels/{channel}/catalog-bindings/{group}/representation/preview",
                body,
            )
        )["representation"]

    async def set_content(self, root: str, locale: str, title: str) -> None:
        """Меняет контент владельцем Catalog, без SQL в Channels."""
        await self.call(
            "PATCH",
            f"/catalog/items/{root}?locale={locale}",
            {
                "content": {
                    "expected_schema_version": 1,
                    "values": {"title": title, "body": "<p>Опис</p>"},
                }
            },
        )

    async def test_all_platforms_preview_current_catalog_without_writes(self) -> None:
        """Preview не создаёт jobs и не изменяет Catalog, связи или наблюдения площадки."""
        root, positions = await self.catalog()
        await self.set_content(root, "uk", "Назва з Catalog")
        await self.set_content(root, "ru", "Название из Catalog")
        models = (
            CatalogItemModel,
            CatalogBindingGroupModel,
            CatalogBindingItemModel,
            ConnectionModel,
            ExternalPublicationModel,
            SyncRunModel,
            ScheduledJobModel,
        )
        for platform in ("prom", "rozetka", "woocommerce"):
            with self.subTest(platform=platform):
                channel, publications = await self.source(platform)
                group = await self.group(channel, root, positions, publications)
                before = {model: await self.rows(model) for model in models}
                value = await self.preview(channel, group)
                self.assertEqual(value["platform"], platform)
                self.assertEqual(value["binding_state"], "linked")
                self.assertEqual(
                    (value["binding_revision"], value["config_revision"]), (1, 1)
                )
                target = value["targets"][0]
                self.assertTrue(target["ready"])
                self.assertEqual(target["publication_id"], publications[0])
                self.assertIn(
                    target["binding_item_id"],
                    [str(row["id"]) for row in before[CatalogBindingItemModel]],
                )
                content = {item["locale"]: item for item in target["content"]}
                self.assertEqual(content["uk"]["title"], "Назва з Catalog")
                self.assertEqual(
                    content["uk"]["origins"]["title"],
                    {"kind": "catalog", "catalog_position_id": root},
                )
                if platform != "woocommerce":
                    self.assertEqual(content["ru"]["title"], "Название из Catalog")
                self.assertNotIn("raw_data", str(value))
                self.assertNotIn("credentials", str(value))
                self.assertEqual(
                    {model: await self.rows(model) for model in models}, before
                )
                await self.set_content(root, "uk", "Змінена назва")
                current = await self.preview(channel, group, ["uk"])
                self.assertEqual(
                    current["targets"][0]["content"][0]["title"], "Змінена назва"
                )
                await self.set_content(root, "uk", "Назва з Catalog")

    async def test_woo_partial_family_inheritance_and_explicit_clears(self) -> None:
        """Контейнер требует полной семьи, а варианты используют источники по полям."""
        root, positions = await self.catalog(variable=True)
        await self.set_content(root, "uk", "Назва сім'ї")
        await self.call(
            "PATCH",
            f"/catalog/items/{root}/variants/{positions[0]}?locale=uk",
            {
                "content": {"expected_schema_version": 1, "values": {"body": ""}},
                "gallery": {"images": [], "primary_image_id": None},
            },
        )
        channel, publications = await self.source("woocommerce", variable=True)
        group = await self.group(
            channel,
            root,
            positions[:1],
            publications[1:],
            "VARIABLE_TO_VARIABLE",
            publications[0],
        )
        value = await self.preview(channel, group)
        self.assertEqual(value["binding_state"], "partial")
        container, variation = value["targets"]
        self.assertEqual(container["role"], "container")
        self.assertFalse(container["ready"])
        self.assertIn(
            "representation_family_incomplete",
            [issue["code"] for issue in container["issues"]],
        )
        self.assertTrue(variation["ready"])
        self.assertEqual(variation["publication_kind"], "variant")
        content = variation["content"][0]
        self.assertEqual(content["title"], "Назва сім'ї")
        self.assertEqual(content["body"], "")
        self.assertEqual(content["gallery"], [])
        self.assertEqual(
            content["origins"]["title"],
            {"kind": "catalog_parent", "catalog_position_id": root},
        )
        self.assertEqual(
            content["origins"]["body"]["catalog_position_id"], positions[0]
        )

    async def test_prom_variable_family_and_independent_rozetka_targets(self) -> None:
        """Prom сохраняет роли основной позиции, Rozetka допускает независимую частичную пару."""
        root, positions = await self.catalog(variable=True)
        await self.set_content(root, "uk", "Сім'я")
        channel, publications = await self.source("prom", variable=True)
        group = await self.group(
            channel, root, positions, publications, "VARIABLE_TO_VARIABLE"
        )
        value = await self.preview(channel, group, ["uk"])
        self.assertEqual(value["binding_state"], "linked")
        self.assertEqual(len(value["targets"]), 2)
        self.assertTrue(all(target["ready"] for target in value["targets"]))
        self.assertEqual(
            {target["publication_kind"] for target in value["targets"]},
            {"simple", "variant"},
        )
        channel, publications = await self.source("rozetka")
        group = await self.group(
            channel, root, positions[:1], publications, "VARIABLE_TO_SIMPLE"
        )
        value = await self.preview(channel, group, ["uk"])
        self.assertEqual(value["binding_state"], "partial")
        self.assertTrue(value["targets"][0]["ready"])

    async def test_missing_locales_stale_config_and_changed_structure_are_diagnostics(
        self,
    ) -> None:
        """Наблюдаемое название не подставляется вместо отсутствующего Catalog title."""
        root, positions = await self.catalog()
        channel, publications = await self.source()
        group = await self.group(channel, root, positions, publications)
        value = await self.preview(channel, group)
        target = value["targets"][0]
        self.assertFalse(target["ready"])
        self.assertEqual(
            [(issue["field"], issue["locale"]) for issue in target["issues"]],
            [("title", "uk"), ("title", "ru")],
        )
        await self.set_content(root, "uk", "Назва")
        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant, self.naming
            )
            await session.execute(
                update(ConnectionModel)
                .where(ConnectionModel.channel_id == UUID(channel))
                .values(config_revision=2)
            )
            await session.commit()
        value = await self.preview(channel, group, ["uk"])
        self.assertIn(
            "representation_publication_stale",
            [issue["code"] for issue in value["targets"][0]["issues"]],
        )
        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant, self.naming
            )
            await session.execute(
                update(ExternalPublicationModel)
                .where(ExternalPublicationModel.id == UUID(publications[0]))
                .values(kind="variable")
            )
            await session.commit()
        value = await self.preview(channel, group, ["uk"])
        self.assertEqual(value["binding_state"], "conflict")
        self.assertIn(
            "binding_simple_structure_invalid",
            [issue["code"] for issue in value["issues"]],
        )

    async def test_read_snapshot_is_stable_between_locales_during_catalog_edit(
        self,
    ) -> None:
        """Конкурирующая запись после первого языка не смешивается со старым снимком."""
        root, positions = await self.catalog()
        for locale in ("uk", "ru"):
            await self.set_content(root, locale, "Before")
        channel, publications = await self.source()
        group = await self.group(channel, root, positions, publications)
        original = SqlAlchemyCatalogItemQueryRepository.snapshots
        changed = False

        async def read_with_concurrent_change(
            repository: SqlAlchemyCatalogItemQueryRepository,
            identifiers: tuple[UUID, ...],
            locale: str,
            as_of: datetime,
        ) -> tuple[GetCatalogProductSnapshotResultDTO, ...]:
            """Изменяет второй язык после выполнения чтения первого."""
            nonlocal changed
            result = await original(repository, identifiers, locale, as_of)
            if locale == "uk" and not changed:
                changed = True
                await self.set_content(root, "ru", "After")
            return result

        with patch.object(
            SqlAlchemyCatalogItemQueryRepository,
            "snapshots",
            read_with_concurrent_change,
        ):
            value = await self.preview(channel, group)
        self.assertTrue(changed)
        self.assertEqual(
            [item["title"] for item in value["targets"][0]["content"]],
            ["Before", "Before"],
        )
        value = await self.preview(channel, group)
        self.assertEqual(
            [item["title"] for item in value["targets"][0]["content"]],
            ["Before", "After"],
        )

    async def test_auth_csrf_tenant_scope_and_strict_input(self) -> None:
        """Не раскрывает чужие группы и не принимает настройки, секреты или overrides."""
        root, positions = await self.catalog()
        channel, publications = await self.source()
        group = await self.group(channel, root, positions, publications)
        other_channel, _ = await self.source()
        path = f"/channels/{channel}/catalog-bindings/{group}/representation/preview"
        no_csrf = await self.client.post("/api/console" + path, json={})
        self.assertEqual(no_csrf.status_code, 403)
        await self.call(
            "POST",
            f"/channels/{other_channel}/catalog-bindings/{group}/representation/preview",
            {},
            404,
        )
        for payload in (
            {"credentials": {"token": "never-return"}},
            {"overrides": {}},
            {"locales": []},
            {"locales": ["uk", "uk"]},
            {"locales": ["en"]},
        ):
            response = await self.call("POST", path, payload, 422)
            self.assertNotIn("never-return", str(response))
        await self.call(
            "POST",
            f"/channels/{channel}/catalog-bindings/{uuid4()}/representation/preview",
            {},
            404,
        )
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        await self.call("POST", path, {}, 404)
        self.app.state.test_context = self.context

        class Deny:
            """Запрещает чтение через общий authorization port."""

            async def can(self, **kwargs: object) -> bool:
                """Возвращает отказ без обращения к данным группы."""
                return False

        self.app.state.authorization_service = Deny()
        await self.call("POST", path, {}, 403)


def load_tests(loader: TestLoader, tests: TestSuite, pattern: str | None) -> TestSuite:
    """Запускает только новые сценарии, не дублируя унаследованные тесты fixtures."""
    return TestSuite(
        RepresentationPostgresTests(name)
        for name in RepresentationPostgresTests.__dict__
        if name.startswith("test_")
    )
