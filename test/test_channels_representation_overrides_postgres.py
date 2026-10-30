"""Сохранение, ревизии, разрешение и гонки представлений на PostgreSQL и HTTP."""

import asyncio
from dataclasses import replace
from datetime import datetime, UTC
from unittest import TestLoader, TestSuite
from unittest.mock import patch
from uuid import UUID, uuid4

from sqlalchemy import insert, select, text, update

from src.modules.channels.infrastructure.persistence.models.product_representation import (
    ProductRepresentationModel as R,
)
from src.modules.channels.infrastructure.persistence.models.catalog_binding_item import (
    CatalogBindingItemModel as I,
)
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel as N,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel as P,
)
from src.modules.channels.application.product_representation.service.drafts import (
    RepresentationDrafts,
    PreparedRepresentationDraft,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.files.infrastructure.persistence.models.storage_provider import (
    StorageProviderModel,
)
from src.modules.files.infrastructure.persistence.models.bucket import BucketModel
from src.modules.files.infrastructure.persistence.models.stored_file import (
    StoredFileModel,
)
from test import test_channels_representation_postgres as support


class RepresentationOverridesPostgresTests(support.RepresentationPostgresTests):
    """Использует настоящий общий UoW и существующие fixtures сопоставлений."""

    def path(self, channel: str, group: str) -> str:
        """Возвращает базовый путь конкретного представления."""
        return f"/channels/{channel}/catalog-bindings/{group}/representation"

    def version(self, detail: dict) -> dict:
        """Фиксирует контекст, который действительно видел редактор."""
        return {
            "expected_revision": detail["state"]["revision"],
            "expected_binding_revision": detail["binding_revision"],
            "expected_config_revision": detail["config_revision"],
        }

    async def fixture(
        self, *, variable: bool = False
    ) -> tuple[str, str, str, list[str], list[str]]:
        """Создаёт полностью заполненную простую или независимую вариативную группу."""
        root, positions = await self.catalog(variable=variable)
        for locale in ("uk", "ru"):
            await self.set_content(root, locale, "Catalog " + locale)
        channel, publications = await self.source()
        if variable:
            _, additional = await self.source(existing_channel=channel)
            publications += additional
        group = await self.group(
            channel,
            root,
            positions,
            publications,
            "VARIABLE_TO_SIMPLE" if variable else "SIMPLE_TO_SIMPLE",
        )
        return channel, group, root, positions, publications

    async def verified(self, channel: str) -> None:
        """Фиксирует проверенное подключение для теста локального разрешения экспорта."""
        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant, self.naming
            )
            connection = (
                (
                    await session.execute(
                        select(N.__table__).where(N.channel_id == UUID(channel))
                    )
                )
                .mappings()
                .one()
            )
            verification = dict(connection["verification"]) | {
                "status": "verified",
                "checked_at": datetime.now(UTC).isoformat(),
                "error_code": None,
            }
            await session.execute(
                update(N)
                .where(N.id == connection["id"])
                .values(
                    identity_namespace="prom.root_group",
                    identity_key=channel,
                    verification=verification,
                )
            )
            await session.commit()

    async def stored_file(
        self, *, tenant: UUID, content_type: str, status: str = "ready"
    ) -> UUID:
        """Создаёт метаданные Files без сетевого хранилища для проверки границы модулей."""
        provider_id, bucket_id, file_id = uuid4(), uuid4(), uuid4()
        async with self.sessions() as session:
            await bind_tenant_schema(await session.connection(), tenant, self.naming)
            await session.execute(
                insert(StorageProviderModel).values(
                    id=provider_id,
                    name="Representation files fixture",
                    kind="minio",
                    is_system=False,
                    config_ref="fixture",
                )
            )
            await session.execute(
                insert(BucketModel).values(
                    id=bucket_id,
                    provider_id=provider_id,
                    name=bucket_id.hex,
                    status="ready",
                )
            )
            await session.execute(
                insert(StoredFileModel).values(
                    id=file_id,
                    bucket_id=bucket_id,
                    object_key=file_id.hex,
                    name="Representation fixture",
                    content_type=content_type,
                    size_bytes=1,
                    status=status,
                    created_at=datetime.now(UTC),
                )
            )
            await session.commit()
        return file_id

    async def test_lazy_creation_saved_and_draft_preview_reset_and_noop(self) -> None:
        """Чтение не создаёт строку; черновик и сохранённый документ имеют разные пути."""
        channel, group, root, _, _ = await self.fixture()
        path = self.path(channel, group)
        detail = await self.call("GET", path)
        self.assertEqual(
            (
                detail["state"]["id"],
                detail["state"]["revision"],
                detail["state"]["export_enabled"],
            ),
            (None, 0, False),
        )
        self.assertEqual(await self.rows(R), [])
        pair = detail["items"][0]["id"]
        overrides = {
            "common": {"uk": {"title": "Group title"}},
            "items": {pair: {"uk": {"body": "", "gallery": []}}},
        }
        observed = await self.rows(P)
        saved = await self.call(
            "PUT", path, self.version(detail) | {"overrides": overrides}
        )
        self.assertEqual(saved["state"]["revision"], 1)
        before = await self.rows(R)
        same = await self.call(
            "PUT", path, self.version(saved) | {"overrides": overrides}
        )
        self.assertEqual(same, saved)
        self.assertEqual(await self.rows(R), before)
        preview = await self.call("POST", path + "/preview", {})
        content = preview["representation"]["targets"][0]["content"][0]
        self.assertEqual(
            (content["title"], content["body"], content["gallery"]),
            ("Group title", "", []),
        )
        self.assertEqual(content["origins"]["title"]["kind"], "group_override")
        self.assertEqual(content["origins"]["body"]["kind"], "item_override")
        draft = await self.call(
            "POST", path + "/preview", self.version(saved) | {"overrides": {}}
        )
        self.assertTrue(draft["draft"])
        self.assertEqual(
            draft["representation"]["targets"][0]["content"][0]["title"], "Catalog uk"
        )
        self.assertEqual(await self.rows(R), before)
        reset = await self.call("PUT", path, self.version(saved) | {"overrides": {}})
        self.assertEqual(reset["state"]["revision"], 2)
        self.assertEqual(
            (await self.rows(R))[0]["overrides_data"], {"common": {}, "items": {}}
        )
        self.assertEqual(await self.rows(P), observed)

    async def test_groups_languages_and_revision_context_are_independent(self) -> None:
        """Чужая пара и устаревшие версии не перезаписывают ни один документ."""
        channel, group, root, positions, _ = await self.fixture()
        _, other_publications = await self.source(existing_channel=channel)
        other_group = await self.group(channel, root, positions, other_publications)
        path = self.path(channel, group)
        first = await self.call("GET", path)
        saved = await self.call(
            "PUT",
            path,
            self.version(first)
            | {"overrides": {"common": {"uk": {"title": "UK"}, "ru": {"title": "RU"}}}},
        )
        other = await self.call("GET", self.path(channel, other_group))
        self.assertEqual(other["state"]["overrides"], {"common": {}, "items": {}})
        for tokens in (
            self.version(first),
            self.version(saved) | {"expected_binding_revision": 99},
            self.version(saved) | {"expected_config_revision": 99},
        ):
            await self.call("PUT", path, tokens | {"overrides": {}}, 409)
        await self.call(
            "PUT",
            path,
            self.version(saved)
            | {
                "overrides": {
                    "items": {other["items"][0]["id"]: {"uk": {"title": "Foreign"}}}
                }
            },
            422,
        )
        self.assertEqual((await self.call("GET", path))["state"], saved["state"])
        self.assertEqual(len(await self.rows(R)), 1)

    async def test_export_rechecks_verification_content_and_revision_without_sending(
        self,
    ) -> None:
        """Разрешение отдельно от preview; новый неготовый черновик выключает его."""
        root, positions = await self.catalog()
        await self.set_content(root, "uk", "Catalog uk")
        channel, publications = await self.source()
        group = await self.group(channel, root, positions, publications)
        path = self.path(channel, group)
        detail = await self.call("GET", path)
        await self.call("POST", path + "/enable", self.version(detail), 409)
        saved = await self.call(
            "PUT",
            path,
            self.version(detail)
            | {"overrides": {"common": {"ru": {"title": "RU override"}}}},
        )
        await self.call("POST", path + "/enable", self.version(saved), 422)
        await self.verified(channel)
        enabled = await self.call("POST", path + "/enable", self.version(saved))
        self.assertEqual(
            (enabled["state"]["revision"], enabled["state"]["export_enabled"]),
            (2, True),
        )
        repeated = await self.call("POST", path + "/enable", self.version(enabled))
        self.assertEqual(repeated, enabled)
        await self.call("POST", path + "/preview", {})
        self.assertTrue((await self.call("GET", path))["state"]["export_enabled"])
        changed = await self.call(
            "PUT",
            path,
            self.version(enabled)
            | {
                "overrides": {
                    "common": {
                        "uk": {"title": "Changed"},
                        "ru": {"title": "RU override"},
                    }
                }
            },
        )
        self.assertEqual(
            (changed["state"]["revision"], changed["state"]["export_enabled"]),
            (3, True),
        )
        disabled = await self.call(
            "PUT", path, self.version(changed) | {"overrides": {}}
        )
        self.assertEqual(
            (disabled["state"]["revision"], disabled["state"]["export_enabled"]),
            (4, False),
        )
        await self.call("POST", path + "/enable", self.version(disabled), 422)
        self.assertEqual(
            await self.call("POST", path + "/disable", self.version(disabled)), disabled
        )

    async def test_binding_update_preserves_row_and_overrides_of_unchanged_pair(
        self,
    ) -> None:
        """UUID и xmin неизменной строки не меняются, а новая пара не получает старый override."""
        channel, group, root, positions, pubs = await self.fixture(variable=True)
        await self.verified(channel)
        path = self.path(channel, group)
        detail = await self.call("GET", path)
        items = {item["catalog_position_id"]: item["id"] for item in detail["items"]}
        saved = await self.call(
            "PUT",
            path,
            self.version(detail)
            | {
                "overrides": {
                    "common": {"uk": {"title": "Common"}},
                    "items": {
                        identifier: {"uk": {"body": identifier}}
                        for identifier in items.values()
                    },
                }
            },
        )
        enabled = await self.call("POST", path + "/enable", self.version(saved))
        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant, self.naming
            )
            before = dict(
                (
                    await session.execute(
                        select(I.id, text("xmin::text")).where(
                            I.group_id == UUID(group)
                        )
                    )
                ).all()
            )
        _, added = await self.source(existing_channel=channel)
        payload, preview = await self.propose(
            channel,
            root,
            positions,
            [pubs[0], added[0]],
            "VARIABLE_TO_SIMPLE",
            group_id=group,
        )
        update_body = {
            "expected_revision": 1,
            "items": payload["items"],
            "catalog_token": preview["catalog_token"],
            "publication_token": preview["publication_token"],
            "locale": "uk",
        }
        changed = await self.call(
            "PUT", f"/channels/{channel}/catalog-bindings/{group}", update_body
        )
        self.assertEqual(changed["revision"], 2)
        current = await self.call("GET", path)
        self.assertFalse(current["state"]["export_enabled"])
        self.assertEqual(current["state"]["revision"], enabled["state"]["revision"] + 1)
        self.assertEqual(
            set(current["state"]["overrides"]["items"]), {items[positions[0]]}
        )
        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant, self.naming
            )
            after = dict(
                (
                    await session.execute(
                        select(I.id, text("xmin::text")).where(
                            I.group_id == UUID(group)
                        )
                    )
                ).all()
            )
        self.assertEqual(
            before[UUID(items[positions[0]])], after[UUID(items[positions[0]])]
        )
        await self.call("PUT", path, self.version(enabled) | {"overrides": {}}, 409)
        enabled = await self.call("POST", path + "/enable", self.version(current))
        await self.call(
            "PUT",
            f"/channels/{channel}/catalog-bindings/{group}",
            update_body | {"expected_revision": 2},
        )
        self.assertEqual((await self.call("GET", path))["state"], enabled["state"])

    async def test_concurrent_first_saves_cannot_overwrite_each_other(self) -> None:
        """Общая блокировка сериализует отсутствие строки и ожидаемую нулевую ревизию."""
        channel, group, _, _, _ = await self.fixture()
        path = self.path(channel, group)
        detail = await self.call("GET", path)
        payload = self.version(detail) | {"overrides": {}}
        responses = await asyncio.gather(
            *(
                self.client.put(
                    "/api/console" + path, headers=self.headers, json=payload
                )
                for _ in range(2)
            )
        )
        self.assertEqual(
            sorted(response.status_code for response in responses), [200, 409]
        )
        rows = await self.rows(R)
        self.assertEqual((len(rows), rows[0]["revision"]), (1, 1))

    async def test_binding_change_after_concurrent_enable_leaves_export_disabled(
        self,
    ) -> None:
        """Ожидающее изменение состава аннулирует только что выданное разрешение."""
        channel, group, root, positions, pubs = await self.fixture(variable=True)
        await self.verified(channel)
        path = self.path(channel, group)
        detail = await self.call("GET", path)
        saved = await self.call("PUT", path, self.version(detail) | {"overrides": {}})
        payload, preview = await self.propose(
            channel, root, positions[:1], pubs[:1], "VARIABLE_TO_SIMPLE", group_id=group
        )
        body = {
            "expected_revision": 1,
            "items": payload["items"],
            "catalog_token": preview["catalog_token"],
            "publication_token": preview["publication_token"],
            "locale": "uk",
        }
        entered, release = asyncio.Event(), asyncio.Event()
        original = RepresentationDrafts.prepare

        async def hold(
            drafts: RepresentationDrafts, **kwargs: object
        ) -> PreparedRepresentationDraft:
            """Приостанавливает проверку после получения общих блокировок."""
            entered.set()
            await release.wait()
            return await original(drafts, **kwargs)

        with patch.object(RepresentationDrafts, "prepare", hold):
            enable = asyncio.create_task(
                self.client.post(
                    "/api/console" + path + "/enable",
                    headers=self.headers,
                    json=self.version(saved),
                )
            )
            await asyncio.wait_for(entered.wait(), 5)
            change = asyncio.create_task(
                self.client.put(
                    f"/api/console/channels/{channel}/catalog-bindings/{group}",
                    headers=self.headers,
                    json=body,
                )
            )
            release.set()
            responses = await asyncio.gather(enable, change)
        self.assertEqual([response.status_code for response in responses], [200, 200])
        self.assertFalse((await self.call("GET", path))["state"]["export_enabled"])

    async def test_invalid_files_html_and_empty_title_do_not_leave_partial_state(
        self,
    ) -> None:
        """Сервер очищает HTML, проверяет Files и не сохраняет невалидный документ."""
        channel, group, _, _, _ = await self.fixture()
        path = self.path(channel, group)
        detail = await self.call("GET", path)
        for fields in (
            {"title": " "},
            {"gallery": [{"file_id": str(uuid4())}]},
            {"unknown": "value"},
        ):
            await self.call(
                "PUT",
                path,
                self.version(detail) | {"overrides": {"common": {"uk": fields}}},
                422,
            )
        self.assertEqual(await self.rows(R), [])
        saved = await self.call(
            "PUT",
            path,
            self.version(detail)
            | {
                "overrides": {
                    "common": {
                        "uk": {
                            "body": '<p>Safe</p><script>alert(1)</script><img src="x" onerror="alert(1)">'
                        }
                    }
                }
            },
        )
        html = saved["state"]["overrides"]["common"]["uk"]["body"]
        self.assertIn("<p>Safe</p>", html)
        self.assertNotIn("script", html)
        self.assertNotIn("onerror", html)
        await self.call("POST", path + "/preview", {"overrides": {}}, 422)
        await self.call("POST", path + "/preview", {"overrides": None}, 422)
        self.assertEqual((await self.call("GET", path))["state"], saved["state"])

    async def test_gallery_checks_tenant_mime_and_ready_without_storage_calls(
        self,
    ) -> None:
        """Галерея принимает ready-изображение, а чужой файл, PDF и uploading отклоняет."""
        channel, group, _, _, _ = await self.fixture()
        path = self.path(channel, group)
        detail = await self.call("GET", path)
        ready = await self.stored_file(tenant=self.tenant, content_type="image/png")
        foreign = await self.stored_file(tenant=self.other, content_type="image/png")
        pdf = await self.stored_file(tenant=self.tenant, content_type="application/pdf")
        uploading = await self.stored_file(
            tenant=self.tenant, content_type="image/png", status="uploading"
        )
        for identifier in (foreign, pdf, uploading):
            await self.call(
                "PUT",
                path,
                self.version(detail)
                | {
                    "overrides": {
                        "common": {"uk": {"gallery": [{"file_id": str(identifier)}]}}
                    }
                },
                422,
            )
        self.assertEqual(await self.rows(R), [])
        saved = await self.call(
            "PUT",
            path,
            self.version(detail)
            | {
                "overrides": {
                    "common": {
                        "uk": {"gallery": [{"file_id": str(ready), "alt": "Image"}]}
                    }
                }
            },
        )
        await self.verified(channel)
        await self.call("POST", path + "/enable", self.version(saved))
        preview = await self.call("POST", path + "/preview", {})
        self.assertEqual(
            preview["representation"]["targets"][0]["content"][0]["gallery"],
            [{"file_id": str(ready), "alt": "Image", "caption": ""}],
        )

    async def test_new_endpoints_enforce_manage_csrf_and_tenant_scope(self) -> None:
        """Чтение требует read, команды — manage и CSRF; чужой tenant не видит группу."""
        channel, group, _, _, _ = await self.fixture()
        path = self.path(channel, group)
        detail = await self.call("GET", path)
        commands = (
            ("PUT", path, self.version(detail) | {"overrides": {}}),
            ("POST", path + "/enable", self.version(detail)),
            ("POST", path + "/disable", self.version(detail)),
        )
        for method, endpoint, payload in commands:
            response = await self.client.request(
                method, "/api/console" + endpoint, json=payload
            )
            self.assertEqual(response.status_code, 403, response.text)

        class ReadOnly:
            """Разрешает чтение, но запрещает изменение Channels."""

            async def can(self, **kwargs: object) -> bool:
                """Проверяет переданное право внешнего authorization port."""
                return kwargs.get("action") == "channels.read"

        self.app.state.authorization_service = ReadOnly()
        await self.call("GET", path)
        for method, endpoint, payload in commands:
            await self.call(method, endpoint, payload, 403)
        del self.app.state.authorization_service
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        await self.call("GET", path, status=404)
        for method, endpoint, payload in commands:
            await self.call(method, endpoint, payload, 404)
        self.app.state.test_context = self.context
        self.assertEqual(await self.rows(R), [])

    async def test_migration_roundtrip_and_cascade_keep_catalog_and_publications(
        self,
    ) -> None:
        """Миграция не заполняет defaults и каскад удаляет только локальное намерение."""
        channel, group, root, positions, publications = await self.fixture()
        path = self.path(channel, group)
        detail = await self.call("GET", path)
        await self.call("POST", path + "/disable", self.version(detail))
        self.assertEqual(await self.rows(R), [])
        await self.call("PUT", path, self.version(detail) | {"overrides": {}})
        async with self.engine.begin() as connection:
            await TenantMigrator().downgrade(
                connection, self.schemas[0], "0010_channels_stock_sync"
            )
            await TenantMigrator().upgrade(connection, self.schemas[0])
        self.assertEqual((await self.call("GET", path))["state"]["revision"], 0)
        await self.call("PUT", path, self.version(detail) | {"overrides": {}})
        await self.call(
            "DELETE",
            f"/channels/{channel}/catalog-bindings/{group}?expected_revision=1",
            status=204,
        )
        self.assertEqual(await self.rows(R), [])
        self.assertEqual(len(await self.rows(P)), 1)
        await self.call("GET", f"/catalog/items/{root}?locale=uk")
        group = await self.group(channel, root, positions, publications)
        path = self.path(channel, group)
        detail = await self.call("GET", path)
        await self.call("PUT", path, self.version(detail) | {"overrides": {}})
        channel_detail = await self.call("GET", f"/channels/{channel}")
        await self.call(
            "DELETE",
            f"/channels/{channel}?expected_revision={channel_detail['revision']}",
            status=204,
        )
        self.assertEqual(await self.rows(R), [])
        await self.call("GET", f"/catalog/items/{root}?locale=uk")


def load_tests(loader: TestLoader, tests: TestSuite, pattern: str | None) -> TestSuite:
    """Запускает новые сценарии без дублирования унаследованных fixtures-тестов."""
    return TestSuite(
        RepresentationOverridesPostgresTests(name)
        for name in RepresentationOverridesPostgresTests.__dict__
        if name.startswith("test_")
    )
