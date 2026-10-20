"""Ручное обновление: реальный API/CSRF, PostgreSQL, durable jobs и fixture площадки."""

import asyncio
from datetime import UTC, datetime
import os
import unittest
from uuid import UUID, uuid4
from sqlalchemy import select, update
from src.modules.channels.application.plugin_contract import HttpResultDTO
from src.modules.channels.application.port.plugin_services import PluginCallError
from src.modules.channels.infrastructure.jobs import CONTENT_UPDATE_JOB
from src.modules.channels.presentation.jobs.content_update import (
    ChannelsContentUpdateJobHandler,
)
from src.modules.channels.presentation.content_update.assembly import (
    build_content_update_handlers,
)
from src.modules.channels.application.content_update.command.prepare_content_update_step.command import (
    PrepareContentUpdateStepCommand,
)
from src.modules.channels.infrastructure.persistence.models.content_update import (
    ContentUpdateRunModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_content_value import (
    CatalogItemContentValueModel,
)
from src.modules.shared.infrastructure.jobs.sqlalchemy_scheduled_job_repository import (
    SqlAlchemyScheduledJobRepository,
)
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from test import test_channels_bindings_postgres as bindings
from test import test_channels_postgres as core
from test.channels_import_support import FullPublicationTransport


class ContentTransport(FullPublicationTransport):
    """Эмулирует существующие карточки и сохраняет исключительно разрешённые записи."""

    def __init__(self) -> None:
        """Готовит управляемые неопределённые ответы и внешние изменения."""
        super().__init__()
        self.values: dict[str, dict[str, str]] = {}
        self.writes: list[tuple[str, dict[str, str]]] = []
        self.lose_response = False
        self.missing = False
        self.fail_id: str | None = None

    async def get(
        self,
        path: str,
        *,
        query: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResultDTO:
        """Возвращает изменяемые тексты, сохраняя остальные поля исходной fixture."""
        result = await super().get(path, query=query, headers=headers)
        if (
            path.startswith("/wp-json/wc/v3/products/")
            and path.rsplit("/", 1)[-1].isdecimal()
        ):
            if self.missing:
                raise PluginCallError("publication_not_found")
            result.body.update(self.values.get(path, {}))
        return result

    async def put(
        self,
        path: str,
        *,
        payload: dict[str, str],
        headers: dict[str, str] | None = None,
    ) -> HttpResultDTO:
        """Не создаёт цели и позволяет потерять ответ после сохранения записи."""
        assert set(payload) == {"name", "description"}
        assert headers and "Authorization" in headers
        if self.missing:
            raise PluginCallError("publication_not_found")
        if path.endswith("/" + str(self.fail_id)):
            raise PluginCallError("permission_denied")
        self.writes.append((path, dict(payload)))
        self.values[path] = dict(payload)
        if self.lose_response:
            self.lose_response = False
            raise PluginCallError("network_error")
        return HttpResultDTO({"id": int(path.rsplit("/", 1)[-1]), **payload}, {})


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Requires disposable PostgreSQL"
)
class ChannelsContentUpdatePostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет готовый сценарий на production сборках без внешних магазинов."""

    session = core.ChannelsPostgresTests.session
    request = core.ChannelsPostgresTests.request
    create = core.ChannelsPostgresTests.create
    claim = core.ChannelsPostgresTests.claim
    drain = core.ChannelsPostgresTests.drain
    catalog = bindings.ChannelsBindingsPostgresTests.catalog
    asyncTearDown = core.ChannelsPostgresTests.asyncTearDown

    async def asyncSetUp(self) -> None:
        """Создаёт две изолированные схемы и общую fixture read/write транспорта."""
        await bindings.ChannelsBindingsPostgresTests.asyncSetUp(self)
        self.transport = ContentTransport()
        self.worker = ChannelsContentUpdateJobHandler(
            self.sessions,
            transport_factory=lambda _: self.transport,
            encryption_key=self.key,
        )
        self.verify_worker.transport_factory = lambda _: self.transport
        self.page_worker.transport_factory = lambda _: self.transport

    async def deliver(self, job: ScheduledJob) -> None:
        """Использует штатный worker и настоящий lease очереди."""
        if job.job_type != CONTENT_UPDATE_JOB:
            await core.ChannelsPostgresTests.deliver(self, job)
            return
        await self.worker.handle(job)
        async with self.sessions() as session:
            await SqlAlchemyScheduledJobRepository(session).mark_done(
                job_id=job.id, lock_token=job.lock_token, completed_at=datetime.now(UTC)
            )
            await session.commit()

    async def setup_bound(
        self, kind: str = "woocommerce", count: int = 1, *, empty: bool = False
    ) -> tuple[dict, list[dict], list[str]]:
        """Создаёт обычные товары Catalog и связывает существующие публикации."""
        channel, connection = await self.create(kind)
        await self.drain()
        page = await self.request(
            "GET", f"/connections/{connection['connection_id']}/publications"
        )
        publications = [
            item for item in page["items"] if item["resource_type"] == "product"
        ][:count]
        ids = []
        for index, pub in enumerate(publications):
            item = await self.catalog(
                "POST",
                body=(
                    {}
                    if empty
                    else {
                        "translations": {
                            locale: {
                                "expected_schema_version": 1,
                                "values": {
                                    "title": f"Catalog {locale} {index}",
                                    "body": f"<p>Description {locale} {index}</p>",
                                },
                            }
                            for locale in ("uk", "ru")
                        }
                    }
                ),
                status=201,
            )
            ids.append(item["id"])
            await self.request(
                "POST",
                f"/publications/{pub['publication_id']}/binding",
                {"catalog_item_id": item["id"]},
                201,
            )
        return channel, publications, ids

    async def prepare(
        self, channel: dict, pubs: list[dict], *, identifier: str | None = None
    ) -> dict:
        """Создаёт сравнение, дожидается чтения и возвращает страницу операции."""
        identifier = identifier or str(uuid4())
        await self.request(
            "POST",
            f"/{channel['channel_id']}/content-updates",
            {
                "run_id": identifier,
                "publication_ids": [pub["publication_id"] for pub in pubs],
            },
            202,
        )
        await self.drain()
        return await self.request("GET", "/content-updates/" + identifier)

    async def enable(self, channel: dict, enabled: bool = True) -> None:
        """Явно разрешает исходящие операции через существующий policy endpoint."""
        current = await self.request("GET", "/" + channel["channel_id"])
        await self.request(
            "PATCH",
            "/" + channel["channel_id"],
            {"revision": current["revision"], "is_enabled": enabled},
        )

    async def confirm(self, run: dict, status: int = 202) -> dict:
        """Подтверждает ровно полученный hash и revision."""
        return await self.request(
            "POST",
            f"/content-updates/{run['id']}/confirm",
            {"expected_revision": run["revision"], "preview_hash": run["preview_hash"]},
            status,
        )

    async def test_full_manual_update_only_texts_and_catalog_unchanged(self) -> None:
        """Внешняя запись ограничена двумя полями; Catalog и default-off не меняются при preview."""
        channel, pubs, ids = await self.setup_bound()
        before = await self.catalog("GET", "/" + ids[0] + "?locale=uk")
        run = await self.prepare(channel, pubs)
        self.assertEqual(run["status"], "ready")
        self.assertFalse(run["outbound_enabled"])
        self.assertEqual(self.transport.writes, [])
        await self.confirm(run, 503)
        await self.enable(channel)
        await self.confirm(run)
        await self.drain()
        result = await self.request("GET", "/content-updates/" + run["id"])
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(len(self.transport.writes), 1)
        self.assertEqual(
            self.transport.writes[0][1],
            {"name": "Catalog uk 0", "description": "<p>Description uk 0</p>"},
        )
        self.assertEqual(
            before["item"],
            (await self.catalog("GET", "/" + ids[0] + "?locale=uk"))["item"],
        )
        await self.confirm(run)
        await self.drain()
        self.assertEqual(len(self.transport.writes), 1)
        history = await self.request("GET", f"/{channel['channel_id']}/content-updates")
        self.assertEqual(history["items"][0]["id"], run["id"])
        self.assertNotIn("secret", str(result))

    async def test_prom_two_locales_preview_but_no_unsafe_xml_submission(self) -> None:
        """Prom сравнивает реальные переводы, но запрет XML-записи нельзя обойти подтверждением."""
        channel, pubs, _ = await self.setup_bound("prom")
        run = await self.prepare(channel, pubs)
        self.assertEqual(run["status"], "blocked")
        self.assertEqual(
            [text["locale"] for text in run["items"][0]["observed"]], ["ru", "uk"]
        )
        self.assertIn(
            "content_update_update_only_unconfirmed", run["items"][0]["issues"]
        )
        await self.enable(channel)
        await self.confirm(run, 503)
        self.assertEqual(self.transport.writes, [])

    async def test_unknown_response_reconciles_without_second_write(self) -> None:
        """Потерянный ответ после PUT не вызывает слепой повтор записи."""
        channel, pubs, _ = await self.setup_bound()
        run = await self.prepare(channel, pubs)
        await self.enable(channel)
        self.transport.lose_response = True
        await self.confirm(run)
        await self.drain()
        failed = await self.request("GET", "/content-updates/" + run["id"])
        self.assertEqual(failed["items"][0]["status"], "unknown")
        await self.request(
            "POST",
            f"/content-updates/{run['id']}/retry",
            {"expected_revision": failed["revision"]},
            202,
        )
        await self.drain()
        self.assertEqual(
            (await self.request("GET", "/content-updates/" + run["id"]))["status"],
            "succeeded",
        )
        self.assertEqual(len(self.transport.writes), 1)

    async def test_catalog_change_invalidates_confirmation(self) -> None:
        """Подтверждение не подменяет заранее показанные тексты свежими значениями."""
        channel, pubs, ids = await self.setup_bound()
        run = await self.prepare(channel, pubs)
        async with self.session() as session:
            await session.execute(
                update(CatalogItemContentValueModel)
                .where(CatalogItemContentValueModel.catalog_item_id == UUID(ids[0]))
                .values(value="Changed")
            )
        await self.enable(channel)
        await self.confirm(run, 409)
        self.assertEqual(self.transport.writes, [])

    async def test_external_change_is_not_overwritten(self) -> None:
        """Перед PUT повторно читается исходный текст; чужая правка останавливает отправку."""
        channel, pubs, _ = await self.setup_bound()
        run = await self.prepare(channel, pubs)
        await self.enable(channel)
        self.transport.values["/wp-json/wc/v3/products/" + pubs[0]["external_id"]] = {
            "name": "External edit"
        }
        await self.confirm(run)
        await self.drain()
        result = await self.request("GET", "/content-updates/" + run["id"])
        self.assertIn("external_content_changed", result["items"][0]["issues"])
        self.assertEqual(self.transport.writes, [])

    async def test_concurrent_confirm_and_target_reservation(self) -> None:
        """Дубли подтверждения идемпотентны, два разных запуска не пишут в одну цель."""
        channel, pubs, _ = await self.setup_bound()
        run = await self.prepare(channel, pubs)
        other = await self.prepare(channel, pubs)
        await self.enable(channel)
        await asyncio.gather(self.confirm(run), self.confirm(run))
        await self.confirm(other, 409)
        await self.drain()
        self.assertEqual(len(self.transport.writes), 1)

    async def test_partial_success_and_retry_is_read_only(self) -> None:
        """Успешная позиция сохраняется, проверка ошибки не повторяет запись других позиций."""
        channel, pubs, _ = await self.setup_bound(count=2)
        run = await self.prepare(channel, pubs)
        await self.enable(channel)
        self.transport.fail_id = pubs[1]["external_id"]
        await self.confirm(run)
        await self.drain()
        result = await self.request("GET", "/content-updates/" + run["id"])
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(self.transport.writes), 1)
        await self.request(
            "POST",
            f"/content-updates/{run['id']}/retry",
            {"expected_revision": result["revision"]},
            202,
        )
        await self.drain()
        self.assertEqual(len(self.transport.writes), 1)

    async def test_empty_catalog_and_missing_target_block_preview(self) -> None:
        """Отсутствующие тексты или карточка не превращаются в очистку либо создание."""
        channel, pubs, _ = await self.setup_bound(empty=True)
        run = await self.prepare(channel, pubs)
        self.assertEqual(run["status"], "blocked")
        self.assertIn("catalog_content_missing", run["items"][0]["issues"])
        self.transport.missing = True
        missing = await self.prepare(channel, pubs)
        self.assertEqual(missing["status"], "blocked")
        self.assertIn("publication_not_found", missing["items"][0]["issues"])
        self.assertEqual(self.transport.writes, [])

    async def test_sending_intent_reentry_never_repeats_put(self) -> None:
        """Сбой между intent и внешним вызовом при повторной доставке запускает только сверку."""
        channel, pubs, _ = await self.setup_bound()
        run = await self.prepare(channel, pubs)
        await self.enable(channel)
        await self.confirm(run)
        jobs = await self.claim()
        job = next(job for job in jobs if job.job_type == CONTENT_UPDATE_JOB)
        async with self.session() as session:
            result = await build_content_update_handlers(
                session, self.worker.registry
            ).prepare.execute(
                PrepareContentUpdateStepCommand(
                    self.tenant, UUID(run["id"]), int(job.payload["sequence"])
                )
            )
            self.assertEqual(result.mode, "send")
        await self.deliver(job)
        await self.drain()
        self.assertEqual(self.transport.writes, [])
        result = await self.request("GET", "/content-updates/" + run["id"])
        self.assertEqual(result["items"][0]["status"], "failed")

    async def test_disable_after_confirm_stops_write(self) -> None:
        """Выключение исходящих операций до фонового шага отменяет допуск записи."""
        channel, pubs, _ = await self.setup_bound()
        run = await self.prepare(channel, pubs)
        await self.enable(channel)
        await self.confirm(run)
        await self.enable(channel, False)
        await self.drain()
        self.assertEqual(self.transport.writes, [])
        self.assertEqual(
            (await self.request("GET", "/content-updates/" + run["id"]))["status"],
            "stale",
        )

    async def test_creation_idempotency_rejects_changed_selection(self) -> None:
        """Один ID подготовки нельзя повторно применить к другой публикации."""
        channel, pubs, _ = await self.setup_bound(count=2)
        run = await self.prepare(channel, pubs[:1])
        await self.request(
            "POST",
            f"/{channel['channel_id']}/content-updates",
            {"run_id": run["id"], "publication_ids": [pubs[1]["publication_id"]]},
            409,
        )
        await self.request(
            "POST",
            f"/{channel['channel_id']}/content-updates",
            {"run_id": run["id"], "publication_ids": [pubs[0]["publication_id"]]},
            202,
        )

    async def test_tenant_actor_rights_and_csrf_are_enforced(self) -> None:
        """Чужой tenant/автор и отсутствие прав либо CSRF не дают доступ к операции."""
        from dataclasses import replace
        from types import SimpleNamespace
        from unittest.mock import AsyncMock
        from src.modules.identity.presentation.access.depends import (
            get_authorization_service,
        )

        channel, pubs, _ = await self.setup_bound()
        run = await self.prepare(channel, pubs)
        original = self.app.state.test_context
        self.app.state.test_context = replace(
            original, principal=replace(original.principal, tenant_id=str(self.other))
        )
        await self.request("GET", "/content-updates/" + run["id"], status=404)
        self.app.state.test_context = replace(
            original, principal=replace(original.principal, user_id=str(uuid4()))
        )
        await self.request("GET", "/content-updates/" + run["id"], status=404)
        await self.confirm(run, 404)
        self.app.state.test_context = original
        authorization = SimpleNamespace(
            can=AsyncMock(
                side_effect=lambda **kwargs: kwargs["action"] != "catalog.read"
            )
        )
        self.app.dependency_overrides[get_authorization_service] = lambda: authorization
        await self.request("GET", "/content-updates/" + run["id"], status=403)
        self.app.dependency_overrides.pop(get_authorization_service)
        response = await self.client.post(
            "/api/console/channels/content-updates/" + run["id"] + "/confirm",
            json={
                "expected_revision": run["revision"],
                "preview_hash": run["preview_hash"],
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.transport.writes, [])

    async def test_enqueue_failure_rolls_back_preparation(self) -> None:
        """Корень, позиции и durable job либо сохраняются вместе, либо полностью откатываются."""
        from unittest.mock import patch, AsyncMock

        channel, pubs, _ = await self.setup_bound()
        identifier = str(uuid4())
        body = {"run_id": identifier, "publication_ids": [pubs[0]["publication_id"]]}
        with patch(
            "src.modules.channels.infrastructure.jobs.ScheduledChannelsJobs.content_update",
            new=AsyncMock(side_effect=RuntimeError("fixture_enqueue_failure")),
        ):
            with self.assertRaisesRegex(RuntimeError, "fixture_enqueue_failure"):
                await self.request(
                    "POST", f"/{channel['channel_id']}/content-updates", body, 202
                )
        async with self.session() as session:
            self.assertIsNone(
                await session.scalar(
                    select(ContentUpdateRunModel.id).where(
                        ContentUpdateRunModel.id == UUID(identifier)
                    )
                )
            )
        await self.request(
            "POST", f"/{channel['channel_id']}/content-updates", body, 202
        )
        await self.drain()
        self.assertEqual(
            (await self.request("GET", "/content-updates/" + identifier))["status"],
            "ready",
        )

    async def test_binding_change_blocks_confirmed_intent(self) -> None:
        """Снятая связь останавливает отправку, не уничтожая историю операции."""
        channel, pubs, _ = await self.setup_bound()
        run = await self.prepare(channel, pubs)
        page = await self.request(
            "GET", "/connections/" + pubs[0]["connection_id"] + "/publications"
        )
        pub = next(
            item
            for item in page["items"]
            if item["publication_id"] == pubs[0]["publication_id"]
        )
        await self.request(
            "DELETE",
            "/publications/" + pub["publication_id"] + "/binding",
            {
                "binding_id": pub["binding_id"],
                "expected_revision": pub["representation_revision"],
            },
            204,
        )
        await self.enable(channel)
        await self.confirm(run, 409)
        self.assertEqual(self.transport.writes, [])

    async def test_same_request_id_across_channels_is_serialized(self) -> None:
        """Одинаковый ключ разных каналов даёт один intent и конфликт вместо SQL 500."""
        channel, pubs, _ = await self.setup_bound()
        other_channel, other_pubs, _ = await self.setup_bound("prom")
        identifier = str(uuid4())
        responses = await asyncio.gather(
            *[
                self.client.post(
                    "/api/console/channels/"
                    + selected_channel["channel_id"]
                    + "/content-updates",
                    json={
                        "run_id": identifier,
                        "publication_ids": [selected_pubs[0]["publication_id"]],
                    },
                    headers=self.headers,
                )
                for selected_channel, selected_pubs in (
                    (channel, pubs),
                    (other_channel, other_pubs),
                )
            ]
        )
        self.assertEqual(
            sorted(response.status_code for response in responses), [202, 409]
        )

    async def test_interrupted_sending_job_can_be_reconciled(self) -> None:
        """Пропавшее задание восстанавливается с чтения результата уже выполненного PUT."""
        channel, pubs, _ = await self.setup_bound()
        run = await self.prepare(channel, pubs)
        await self.enable(channel)
        await self.confirm(run)
        job = next(
            job for job in await self.claim() if job.job_type == CONTENT_UPDATE_JOB
        )
        async with self.session() as session:
            prepared = await build_content_update_handlers(
                session, self.worker.registry
            ).prepare.execute(
                PrepareContentUpdateStepCommand(
                    self.tenant, UUID(run["id"]), int(job.payload["sequence"])
                )
            )
        text = prepared.request.desired[0]
        await self.transport.put(
            "/wp-json/wc/v3/products/" + pubs[0]["external_id"],
            payload={"name": text.title, "description": text.body},
            headers={"Authorization": "fixture"},
        )
        async with self.sessions() as session:
            await SqlAlchemyScheduledJobRepository(session).mark_done(
                job_id=job.id, lock_token=job.lock_token, completed_at=datetime.now(UTC)
            )
            await session.commit()
        interrupted = await self.request("GET", "/content-updates/" + run["id"])
        self.assertTrue(interrupted["interrupted"])
        await self.request(
            "POST",
            "/content-updates/" + run["id"] + "/retry",
            {"expected_revision": interrupted["revision"]},
            202,
        )
        await self.drain()
        self.assertEqual(
            (await self.request("GET", "/content-updates/" + run["id"]))["status"],
            "succeeded",
        )
        self.assertEqual(len(self.transport.writes), 1)

    async def test_unknown_delivery_reserves_target_until_reconciliation(self) -> None:
        """Новый preview не позволяет обойти обязательную сверку неизвестной отправки."""
        from unittest.mock import AsyncMock

        channel, pubs, _ = await self.setup_bound()
        run = await self.prepare(channel, pubs)
        await self.enable(channel)
        put = self.transport.put
        self.transport.put = AsyncMock(side_effect=PluginCallError("network_error"))
        await self.confirm(run)
        await self.drain()
        unknown = await self.request("GET", "/content-updates/" + run["id"])
        self.assertEqual(unknown["items"][0]["status"], "unknown")
        self.transport.put = put
        replacement = await self.prepare(channel, pubs)
        await self.confirm(replacement, 409)
        self.assertEqual(self.transport.writes, [])
        self.transport.denied = True
        await self.request(
            "POST",
            "/content-updates/" + run["id"] + "/retry",
            {"expected_revision": unknown["revision"]},
            202,
        )
        await self.drain()
        still_unknown = await self.request("GET", "/content-updates/" + run["id"])
        self.assertEqual(still_unknown["items"][0]["status"], "unknown")
        await self.confirm(replacement, 409)
        self.transport.denied = False
        await self.request(
            "POST",
            "/content-updates/" + run["id"] + "/retry",
            {"expected_revision": still_unknown["revision"]},
            202,
        )
        await self.drain()
        await self.confirm(replacement)
        await self.drain()
        self.assertEqual(
            (await self.request("GET", "/content-updates/" + replacement["id"]))[
                "status"
            ],
            "succeeded",
        )
        self.assertEqual(len(self.transport.writes), 1)
