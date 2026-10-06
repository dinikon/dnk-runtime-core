"""HTTP, миграция, durable страницы и fencing на изолированном PostgreSQL."""

import asyncio
import os
import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from sqlalchemy import select, func, update
from src.modules.shared.infrastructure.jobs.sqlalchemy_scheduled_job_repository import (
    SqlAlchemyScheduledJobRepository,
)
from src.modules.channels.application.publication_import_run.error import (
    PublicationSourceError,
)
from src.modules.channels.application.publication_import_run.port.source import (
    PublicationSourcePage,
)
from src.modules.channels.infrastructure.publication_import_run.source.normalizer import (
    PublicationNormalizer,
)
from src.modules.channels.infrastructure.external_publication.content.html_sanitizer import (
    PublicationHtmlSanitizer,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel,
)
from src.modules.channels.infrastructure.publication_import_run.persistence.repository import (
    SqlAlchemyPublicationImportRunRepository,
)
from src.modules.shared.infrastructure.jobs.scheduled_job_model import ScheduledJobModel
from src.modules.channels.presentation.publication_import_run.depends import (
    PublicationImportJobRuntime,
)
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from test.test_channels_postgres import ChannelsPostgresTests, TEST_URL


@unittest.skipUnless(
    TEST_URL, "Set TEST_POSTGRES_URL to a disposable PostgreSQL database."
)
class ChannelPublicationsPostgresTests(ChannelsPostgresTests):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.normalizer = PublicationNormalizer(PublicationHtmlSanitizer())

    async def drain(self, source):
        runtime = PublicationImportJobRuntime(self.sessions, source, self.cipher)
        for _ in range(15):
            now = datetime.now(UTC)
            async with self.sessions() as session:
                jobs = await SqlAlchemyScheduledJobRepository(session).claim_due_jobs(
                    limit=10,
                    now=now,
                    locked_until=now + timedelta(minutes=2),
                    lock_token=str(uuid4()),
                )
                await session.commit()
            if not jobs:
                return
            for job in jobs:
                try:
                    await runtime.handle(job)
                except PublicationSourceError as error:
                    async with self.sessions() as session:
                        await SqlAlchemyScheduledJobRepository(session).mark_failed(
                            job_id=job.id,
                            lock_token=job.lock_token,
                            error=error.code,
                            retry_at=datetime.now(UTC),
                            failed_at=datetime.now(UTC),
                        )
                        await session.commit()
                    continue
                async with self.sessions() as session:
                    await SqlAlchemyScheduledJobRepository(session).mark_done(
                        job_id=job.id,
                        lock_token=job.lock_token,
                        completed_at=datetime.now(UTC),
                    )
                    await session.commit()
        self.fail("Import did not terminate within 15 bounded pages.")

    async def publication_count(self):
        async with self.sessions() as session:
            return await session.scalar(
                select(func.count())
                .select_from(ExternalPublicationModel)
                .execution_options(schema_translate_map={"tenant": self.schemas[0]})
            )

    async def test_pages_variations_read_http_idempotency_and_tenant_isolation(self):
        channel = await self.create()
        url = self.base + "/" + channel["id"]
        latest = (await self.client.get(url + "/publication-imports/latest")).json()
        self.assertEqual(latest["status"], "queued")
        response = await self.client.post(
            url + "/publication-imports", headers=self.headers
        )
        self.assertEqual(response.status_code, 202, response.text)
        self.assertEqual(response.json()["run_id"], latest["id"])
        parent = self.normalizer.normalize(
            "woocommerce",
            {
                "id": 10,
                "name": "Карточка",
                "type": "variable",
                "variations": [11, 12],
                "price": "0",
                "sku": "P",
                "description": "<p>Описание</p><script>alert(1)</script>",
                "images": [{"src": "https://img.example/product.jpg"}],
                "attributes": [{"name": "Размер", "options": ["S", "M"]}],
                "native_extra": "preserved",
            },
            currency="UAH",
        )
        variants = tuple(
            self.normalizer.normalize(
                "woocommerce",
                {
                    "id": id,
                    "name": name,
                    "sku": name,
                    "price": "1.20",
                    "stock_quantity": 0,
                    "attributes": [{"name": "Размер", "option": name}],
                },
                currency="UAH",
                parent_id="10",
            )
            for id, name in ((11, "S"), (12, "M"))
        )

        async def read(connection, checkpoint):
            self.assertEqual(connection.secrets["consumer_key"], "key-original")
            return (
                PublicationSourcePage((parent,), '{"page": 2}')
                if checkpoint == "{}"
                else PublicationSourcePage(variants, None)
            )

        source = SimpleNamespace(read_page=read)
        await self.drain(source)
        latest = (await self.client.get(url + "/publication-imports/latest")).json()
        self.assertEqual(
            (latest["status"], latest["pages"], latest["resources"]),
            ("succeeded", 2, 3),
        )
        page = (await self.client.get(url + "/publications")).json()
        self.assertEqual(page["total"], 1)
        item = page["items"][0]
        self.assertEqual(item["price"], "0")
        self.assertEqual(item["variations_count"], 2)
        self.assertEqual(item["thumbnail_url"], "https://img.example/product.jpg")
        details = await self.client.get(url + "/publications/" + item["id"])
        self.assertEqual(details.status_code, 200, details.text)
        self.assertEqual(details.json()["attributes"][0]["value"], "S, M")
        self.assertEqual(len(details.json()["variants"]), 2)
        self.assertNotIn("raw_payload", details.text)
        self.assertNotIn("native_extra", details.text)
        self.assertNotIn("script", details.json()["description_html"])
        self.assertEqual(details.json()["variants"][0]["quantity"], "0")
        self.assertEqual(await self.publication_count(), 3)
        response = await self.client.post(
            url + "/publication-imports", headers=self.headers
        )
        self.assertEqual(response.status_code, 202)
        await self.drain(source)
        second = (await self.client.get(url + "/publications/" + item["id"])).json()
        self.assertEqual(second["revision"], 1)
        self.assertEqual(await self.publication_count(), 3)
        # Another tenant cannot read either the channel or its publication by known IDs.
        self.app.state.test_context = RequestContext(
            Principal(str(self.actor), str(self.other), "session", ("member",)),
            None,
            None,
            None,
        )
        self.assertEqual(
            (await self.client.get(url + "/publications")).status_code, 404
        )
        self.assertEqual(
            (await self.client.get(url + "/publications/" + item["id"])).status_code,
            404,
        )
        self.assertEqual(
            (
                await self.client.get(url + "/publication-imports/" + latest["id"])
            ).status_code,
            404,
        )

    async def test_external_read_releases_channel_lock_and_settings_change_fences_write(
        self,
    ):
        channel = await self.create()
        url = self.base + "/" + channel["id"]
        resource = self.normalizer.normalize(
            "woocommerce", {"id": 1, "name": "Old store"}
        )

        async def read(connection, checkpoint):
            # This PATCH would hang if a channel row transaction remained open during source I/O.
            changed = await asyncio.wait_for(
                self.client.patch(
                    url,
                    headers=self.headers,
                    json={
                        "config_version": 1,
                        "connection_settings": {"url": "https://other.example/"},
                    },
                ),
                timeout=2,
            )
            self.assertEqual(changed.status_code, 200, changed.text)
            return PublicationSourcePage((resource,), None)

        await self.drain(SimpleNamespace(read_page=read))
        self.assertEqual(await self.publication_count(), 0)
        self.assertIsNone(
            (await self.client.get(url + "/publication-imports/latest")).json()
        )
        self.assertEqual(
            (await self.client.get(url + "/publications")).json()["total"], 0
        )

    async def test_retry_partial_failure_and_empty_success(self):
        channel = await self.create()
        url = self.base + "/" + channel["id"]
        resource = self.normalizer.normalize("woocommerce", {"id": 1, "name": "Kept"})
        calls = 0

        async def read(connection, checkpoint):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise PublicationSourceError("source_unavailable", retryable=True)
            if checkpoint == "{}":
                return PublicationSourcePage((resource,), '{"page": 2}')
            raise PublicationSourceError("access_denied")

        await self.drain(SimpleNamespace(read_page=read))
        latest = (await self.client.get(url + "/publication-imports/latest")).json()
        self.assertEqual(
            (latest["status"], latest["resources"], latest["error_code"]),
            ("partial", 1, "access_denied"),
        )
        self.assertEqual(await self.publication_count(), 1)
        # An independent empty source succeeds with zero resources.
        other = await self.create()
        other_url = self.base + "/" + other["id"]
        await self.drain(
            SimpleNamespace(
                read_page=AsyncMock(return_value=PublicationSourcePage((), None))
            )
        )
        latest = (
            await self.client.get(other_url + "/publication-imports/latest")
        ).json()
        self.assertEqual((latest["status"], latest["resources"]), ("succeeded", 0))

    async def test_parallel_start_returns_one_run_and_post_requires_csrf(self):
        channel = await self.create()
        url = self.base + "/" + channel["id"] + "/publication-imports"
        self.assertEqual((await self.client.post(url)).status_code, 403)
        responses = await asyncio.gather(
            *[self.client.post(url, headers=self.headers) for _ in range(4)]
        )
        self.assertTrue(all(response.status_code == 202 for response in responses))
        self.assertEqual(len({response.json()["run_id"] for response in responses}), 1)
        self.assertEqual(
            (
                await self.client.get(
                    self.base + "/" + channel["id"] + "/publications?limit=0"
                )
            ).status_code,
            422,
        )

    async def test_page_failure_rolls_back_cards_checkpoint_and_continuation_job(self):
        channel = await self.create()
        url = self.base + "/" + channel["id"]
        resources = tuple(
            self.normalizer.normalize("woocommerce", {"id": id, "name": str(id)})
            for id in (1, 2)
        )
        checkpoints = []

        async def read(connection, checkpoint):
            checkpoints.append(checkpoint)
            return (
                PublicationSourcePage(resources, '{"page": 2}')
                if checkpoint == "{}"
                else PublicationSourcePage((), None)
            )

        now = datetime.now(UTC)
        async with self.sessions() as session:
            jobs = await SqlAlchemyScheduledJobRepository(session).claim_due_jobs(
                limit=1,
                now=now,
                locked_until=now + timedelta(minutes=2),
                lock_token=str(uuid4()),
            )
            await session.commit()
        job = jobs[0]
        runtime = PublicationImportJobRuntime(
            self.sessions, SimpleNamespace(read_page=read), self.cipher
        )
        original_save = SqlAlchemyPublicationImportRunRepository.save

        async def fail_after_save(repository, run):
            await original_save(repository, run)
            if run.pages:
                raise RuntimeError(
                    "Injected failure after writing the page and continuation"
                )

        with patch.object(
            SqlAlchemyPublicationImportRunRepository, "save", fail_after_save
        ):
            with self.assertRaisesRegex(RuntimeError, "Injected failure"):
                await runtime.handle(job)
        self.assertEqual(await self.publication_count(), 0)
        latest = (await self.client.get(url + "/publication-imports/latest")).json()
        self.assertEqual(
            (latest["status"], latest["pages"], latest["resources"]), ("running", 0, 0)
        )
        async with self.sessions() as session:
            count = await session.scalar(
                select(func.count())
                .select_from(ScheduledJobModel)
                .where(ScheduledJobModel.tenant_id == self.tenant)
            )
        self.assertEqual(count, 1)
        await runtime.handle(job)
        async with self.sessions() as session:
            await SqlAlchemyScheduledJobRepository(session).mark_done(
                job_id=job.id, lock_token=job.lock_token, completed_at=datetime.now(UTC)
            )
            await session.commit()
        await self.drain(SimpleNamespace(read_page=read))
        self.assertEqual(checkpoints, ["{}", "{}", '{"page": 2}'])
        self.assertEqual(await self.publication_count(), 2)
        latest = (await self.client.get(url + "/publication-imports/latest")).json()
        self.assertEqual(
            (latest["status"], latest["pages"], latest["resources"]),
            ("succeeded", 2, 2),
        )

    async def test_progress_handles_concurrent_continuation_and_exhausted_job(self):
        channel = await self.create()
        url = self.base + "/" + channel["id"]
        now = datetime.now(UTC)
        async with self.sessions() as session:
            jobs = await SqlAlchemyScheduledJobRepository(session).claim_due_jobs(
                limit=1,
                now=now,
                locked_until=now + timedelta(minutes=2),
                lock_token=str(uuid4()),
            )
            await session.commit()
        job = jobs[0]
        resource = self.normalizer.normalize("woocommerce", {"id": 1, "name": "Kept"})
        runtime = PublicationImportJobRuntime(
            self.sessions,
            SimpleNamespace(
                read_page=AsyncMock(
                    return_value=PublicationSourcePage((resource,), '{"page": 2}')
                )
            ),
            self.cipher,
        )
        original_terminal = SqlAlchemyScheduledJobRepository.terminal_or_missing

        async def finish_page_between_progress_reads(repository, *, tenant_id, job_ids):
            await runtime.handle(job)
            async with self.sessions() as session:
                await SqlAlchemyScheduledJobRepository(session).mark_done(
                    job_id=job.id,
                    lock_token=job.lock_token,
                    completed_at=datetime.now(UTC),
                )
                await session.commit()
            return await original_terminal(
                repository, tenant_id=tenant_id, job_ids=job_ids
            )

        with patch.object(
            SqlAlchemyScheduledJobRepository,
            "terminal_or_missing",
            finish_page_between_progress_reads,
        ):
            response = await self.client.get(url + "/publication-imports/latest")
        self.assertEqual(response.status_code, 200, response.text)
        latest = response.json()
        self.assertEqual(
            (latest["status"], latest["pages"], latest["resources"]), ("running", 1, 1)
        )
        self.assertIsNone(latest["error_code"])
        async with self.sessions() as session:
            await session.execute(
                update(ScheduledJobModel)
                .where(
                    ScheduledJobModel.tenant_id == self.tenant,
                    ScheduledJobModel.id != job.id,
                )
                .values(status="failed")
            )
            await session.commit()
        latest = (await self.client.get(url + "/publication-imports/latest")).json()
        self.assertEqual(
            (latest["status"], latest["error_code"]), ("partial", "worker_exhausted")
        )
        self.assertEqual(await self.publication_count(), 1)
        restarted = await self.client.post(
            url + "/publication-imports", headers=self.headers
        )
        self.assertEqual(restarted.status_code, 202, restarted.text)
        self.assertNotEqual(restarted.json()["run_id"], latest["id"])


if __name__ == "__main__":
    unittest.main()
