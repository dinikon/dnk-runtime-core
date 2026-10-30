"""Настоящий SQL/HTTP: ограниченные URL, повторное использование и удаление Files."""

import asyncio
import os
from io import BytesIO
from dataclasses import replace
from datetime import UTC, datetime
from unittest import TestLoader, TestSuite, skipUnless
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

from fastapi import HTTPException, Request
from sqlalchemy import update
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.modules.channels.application.content_media.command.begin_media_transfer.command import (
    BeginMediaTransferCommand,
)
from src.modules.channels.application.content_media.command.begin_media_transfer.handler import (
    BeginMediaTransferHandler,
)
from src.modules.channels.application.content_media.command.record_media_transfer_result.command import (
    RecordMediaTransferResultCommand,
)
from src.modules.channels.application.content_media.command.record_media_transfer_result.handler import (
    RecordMediaTransferResultHandler,
)
from src.modules.channels.application.content_media.contracts import (
    PreparedGallery,
    PreparedGalleryImage,
)
from src.modules.channels.domain.content_media.error import ContentMediaError
from src.modules.channels.domain.content_media.value_object import MediaTransferStatus
from src.modules.channels.infrastructure.persistence.models.content_media import (
    ContentMediaModel,
)
from src.modules.channels.infrastructure.content_media.query_repository import (
    SqlAlchemyContentMediaQueryRepository,
)
from src.modules.channels.infrastructure.platforms.woocommerce.media import (
    WooGalleryAdapter,
)
from src.modules.channels.infrastructure.platforms.woocommerce.models import (
    WooCommerceConfig,
    WooCommerceCredentials,
)
from src.modules.channels.infrastructure.registry import InstalledPlatforms
from src.modules.channels.presentation.content_media.assembly import (
    build_content_media_runtime,
    ContentMediaRuntime,
)
from src.modules.channels.presentation.content_media.depends import (
    get_media_tenant,
    MediaTenant,
    MediaTenantDep,
    get_content_media_runtime,
)
from src.modules.channels.presentation.content_media.router import public_router
from src.modules.files.infrastructure.persistence.models.stored_file import (
    StoredFileModel,
)
from src.modules.files.presentation.router import router as files_router
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator
from src.modules.shared.presentation.crypto.depends import get_cipher
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from test.test_channels_representation_overrides_postgres import (
    RepresentationOverridesPostgresTests,
)
from test.content_media_support import MemoryImageStorage, PNG


class ContentMediaPostgresTests(RepresentationOverridesPostgresTests):
    """Переиспользует реальные Channels/Catalog/UoW, подменяя только owned storage."""

    async def asyncSetUp(self) -> None:
        """Подключает публичный router и контролируемое хранилище к tenant HTTP fixture."""
        await super().asyncSetUp()
        self.app.include_router(public_router)
        self.app.include_router(files_router, prefix="/api/console")
        self.context = replace(
            self.context, principal=replace(self.context.principal, roles=("admin",))
        )
        self.app.state.test_context = self.context
        self.storage = MemoryImageStorage()

        async def tenant(request: Request) -> MediaTenant:
            """Моделирует результат доверенного Tenancy, не авторизацию media."""
            if request.url.hostname != "tenant.example":
                raise HTTPException(404)
            return MediaTenant(
                UUID(self.app.state.test_context.principal.tenant_id),
                "https://tenant.example",
            )

        async def runtime(uow: UoWDep, tenant: MediaTenantDep) -> ContentMediaRuntime:
            """Проверяет отсутствие SQL-транзакции при каждом storage.open."""
            session = uow.session
            self.storage.before_open = lambda: self.assertFalse(
                session.in_transaction(), "storage opened inside SQL transaction"
            )
            return build_content_media_runtime(
                session=session,
                tenant_id=tenant.id,
                base_url=tenant.base_url,
                uow=uow,
                cipher=self.cipher,
                clock=UtcClock(),
                uuid=UUID7Generator(),
                platforms=InstalledPlatforms(),
                storage=self.storage,
            )

        self.app.dependency_overrides[get_media_tenant] = tenant
        self.app.dependency_overrides[get_content_media_runtime] = runtime
        self.app.dependency_overrides[get_cipher] = lambda: self.cipher

    async def image(
        self, *, tenant: UUID | None = None, data: bytes = PNG, mime: str = "image/png"
    ) -> UUID:
        """Создаёт Files metadata и отдельный owned объект без Console upload."""
        tenant = tenant or self.tenant
        identifier = await self.stored_file(tenant=tenant, content_type=mime)
        async with self.sessions() as session:
            await bind_tenant_schema(await session.connection(), tenant, self.naming)
            await session.execute(
                update(StoredFileModel)
                .where(StoredFileModel.id == identifier)
                .values(size_bytes=len(data))
            )
            await session.commit()
        self.storage.objects[(tenant, identifier.hex)] = data
        return identifier

    async def media_fixture(
        self, platform: str = "prom"
    ) -> tuple[str, str, str, dict, list[UUID]]:
        """Создаёт разрешённое представление с двумя изображениями в заданном порядке."""
        root, positions = await self.catalog()
        for locale in ("uk", "ru"):
            await self.set_content(root, locale, "Title " + locale)
        channel, publications = await self.source(platform)
        if platform == "woocommerce":
            from src.modules.channels.infrastructure.persistence.models.external_publication import (
                ExternalPublicationModel,
            )

            async with self.sessions() as session:
                await bind_tenant_schema(
                    await session.connection(), self.tenant, self.naming
                )
                await session.execute(
                    update(ExternalPublicationModel)
                    .where(ExternalPublicationModel.id == UUID(publications[0]))
                    .values(external_id="101")
                )
                await session.commit()
        group = await self.group(channel, root, positions, publications)
        images = [await self.image(), await self.image()]
        path = self.path(channel, group)
        detail = await self.call("GET", path)
        saved = await self.call(
            "PUT",
            path,
            self.version(detail)
            | {
                "overrides": {
                    "common": {
                        "uk": {
                            "gallery": [
                                {"file_id": str(images[0]), "alt": "Front"},
                                {"file_id": str(images[1]), "alt": "Back"},
                            ]
                        }
                    }
                }
            },
        )
        await self.verified(channel)
        enabled = await self.call("POST", path + "/enable", self.version(saved))
        return channel, group, root, enabled, images

    async def prepare_media(self, channel: str, group: str, detail: dict) -> dict:
        """Вызывает настоящий authenticated HTTP с тремя expected-revision токенами."""
        return await self.call(
            "POST", self.path(channel, group) + "/gallery/prepare", self.version(detail)
        )

    async def test_anonymous_get_head_rotation_revocation_and_current_use(self) -> None:
        """URL не зависит от сессии; чужие и устаревшие разрешения не дают байты."""
        channel, group, _, detail, images = await self.media_fixture()
        self.assertEqual(await self.rows(ContentMediaModel), [])
        await self.call("POST", self.path(channel, group) + "/preview", {})
        self.assertEqual(await self.rows(ContentMediaModel), [])
        prepared = await self.prepare_media(channel, group, detail)
        gallery = prepared["galleries"][0]
        self.assertEqual(
            [image["file_id"] for image in gallery["images"]], list(map(str, images))
        )
        self.assertEqual(
            [image["alt"] for image in gallery["images"]], ["Front", "Back"]
        )
        image = gallery["images"][0]
        self.assertIn("image.png?token=", image["url"])
        self.assertNotIn("access_token_hash", str(prepared))
        same = await self.prepare_media(channel, group, detail)
        self.assertEqual(same, prepared)

        async def deny() -> None:
            """Доказывает отсутствие authenticated dependency у public GET/HEAD."""
            raise HTTPException(401)

        self.app.dependency_overrides[require_authenticated_request_context] = deny
        response = await self.client.get(image["url"], headers={"Cookie": ""})
        self.assertEqual(
            (response.status_code, response.content), (200, PNG), response.text
        )
        self.assertEqual(response.headers["content-type"], "image/png")
        self.assertIn("no-store", response.headers["cache-control"])
        head = await self.client.head(image["url"], headers={"Cookie": ""})
        self.assertEqual(
            (head.status_code, head.content, head.headers["content-length"]),
            (200, b"", str(len(PNG))),
        )
        self.assertTrue(all(stream.closed for stream in self.storage.streams))
        invalid = await self.client.get(image["url"].split("token=")[0] + "token=bad")
        self.assertEqual(invalid.status_code, 404)
        wrong_extension = await self.client.get(
            image["url"].replace("image.png", "image.jpg")
        )
        self.assertEqual(wrong_extension.status_code, 404)
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        self.assertEqual((await self.client.get(image["url"])).status_code, 404)
        self.app.state.test_context = self.context
        del self.app.dependency_overrides[require_authenticated_request_context]
        revoked = await self.call(
            "POST",
            f"/channels/{channel}/content-media/{image['media_id']}/revoke",
            {"expected_revision": 1},
        )
        self.assertEqual((await self.client.get(image["url"])).status_code, 404)
        renewed = await self.call(
            "POST",
            f"/channels/{channel}/content-media/{image['media_id']}/renew",
            {"expected_revision": revoked["revision"]},
        )
        self.assertNotEqual(renewed["url"], image["url"])
        self.assertEqual((await self.client.get(renewed["url"])).status_code, 200)
        await self.call(
            "POST", self.path(channel, group) + "/disable", self.version(detail)
        )
        self.assertEqual((await self.client.get(renewed["url"])).status_code, 404)

    async def test_prepare_checks_files_acl_storage_and_context_before_creating_rows(
        self,
    ) -> None:
        """Отказы прав, storage и stale revision не публикуют даже часть галереи."""
        channel, group, _, detail, images = await self.media_fixture()

        class DenyFiles:
            """Разрешает Channels, но не чтение выбранных Files."""

            async def can(self, **kwargs: object) -> bool:
                """Проверяет ресурсное право."""
                return kwargs["action"] != "files.read"

        self.app.state.authorization_service = DenyFiles()
        await self.call(
            "POST",
            self.path(channel, group) + "/gallery/prepare",
            self.version(detail),
            403,
        )
        del self.app.state.authorization_service
        await self.call(
            "POST",
            self.path(channel, group) + "/gallery/prepare",
            self.version(detail) | {"expected_revision": 999},
            409,
        )
        self.storage.objects[(self.tenant, images[1].hex)] = (
            b"<html>invalid image</html>"
        )
        await self.call(
            "POST",
            self.path(channel, group) + "/gallery/prepare",
            self.version(detail),
            422,
        )
        self.assertEqual(await self.rows(ContentMediaModel), [])
        self.assertTrue(all(stream.closed for stream in self.storage.streams))

    def runtime(self, uow: UnitOfWork) -> ContentMediaRuntime:
        """Собирает тот же runtime для тестового исполнителя вне HTTP."""
        return build_content_media_runtime(
            session=uow.session,
            tenant_id=self.tenant,
            base_url="https://tenant.example",
            uow=uow,
            cipher=self.cipher,
            clock=UtcClock(),
            uuid=UUID7Generator(),
            platforms=InstalledPlatforms(),
            storage=self.storage,
        )

    async def test_woo_transfer_records_ids_repeat_reuses_them_and_alt_is_independent(
        self,
    ) -> None:
        """Первый images-only запрос получает ID, повтор не содержит src и не загружает заново."""
        channel, group, _, detail, _ = await self.media_fixture("woocommerce")
        prepared = await self.prepare_media(channel, group, detail)
        value = prepared["galleries"][0]
        gallery = PreparedGallery(
            UUID(value["publication_id"]),
            value["external_id"],
            value["parent_external_id"],
            value["publication_kind"],
            value["locale"],
            tuple(
                PreparedGalleryImage(
                    UUID(image["media_id"]),
                    image["revision"],
                    UUID(image["file_id"]),
                    image["alt"],
                    image["caption"],
                    None,
                    MediaTransferStatus.PENDING,
                    image["url"],
                )
                for image in value["images"]
            ),
        )
        operation = uuid4()
        async with self.engine.connect() as connection:
            async with UnitOfWork(
                async_sessionmaker(connection, expire_on_commit=False)
            ) as uow:
                await bind_tenant_schema(
                    await uow.session.connection(), self.tenant, self.naming
                )
                runtime = self.runtime(uow)
                reserved = await BeginMediaTransferHandler(runtime.transfers).execute(
                    BeginMediaTransferCommand(
                        self.tenant,
                        UUID(channel),
                        UUID(group),
                        detail["state"]["revision"],
                        detail["binding_revision"],
                        detail["config_revision"],
                        tuple(
                            (image.media_id, image.revision) for image in gallery.images
                        ),
                        operation,
                    )
                )
                await uow.commit()

                session = uow.session

                async def send(*args: object, **kwargs: object) -> dict:
                    """Проверяет API вне SQL и возвращает стабильные attachment IDs."""
                    self.assertFalse(session.in_transaction())
                    return {
                        "images": [
                            {"id": 70 + i, "alt": image.alt}
                            for i, image in enumerate(gallery.images)
                        ]
                    }

                http = Mock()
                http.request = AsyncMock(side_effect=send)
                adapter = WooGalleryAdapter(http)
                config = WooCommerceConfig.model_validate(
                    {"version": 1, "endpoint": "https://shop.example", "settings": {}}
                )
                credentials = WooCommerceCredentials(
                    consumer_key="key", consumer_secret="secret"
                )
                results = await adapter.update(
                    config=config,
                    credentials=credentials,
                    gallery=gallery,
                    reserved_media_ids=reserved.media_ids,
                )
                for result in results:
                    recorded = await RecordMediaTransferResultHandler(
                        runtime.transfers
                    ).execute(
                        RecordMediaTransferResultCommand(
                            UUID(channel),
                            1,
                            "prom.root_group",
                            channel,
                            operation,
                            result.media_id,
                            2,
                            result.remote_id,
                            None,
                            False,
                        )
                    )
                    self.assertTrue(recorded.applied)
        repeat = await self.prepare_media(channel, group, detail)
        ids = [image["remote_media_id"] for image in repeat["galleries"][0]["images"]]
        self.assertEqual(ids, ["70", "71"])
        reused = replace(
            gallery,
            images=tuple(
                replace(
                    image,
                    remote_media_id=identifier,
                    transfer_status=MediaTransferStatus.READY,
                )
                for image, identifier in zip(gallery.images, ids)
            ),
        )
        await adapter.update(
            config=config,
            credentials=credentials,
            gallery=reused,
            reserved_media_ids=(),
        )
        self.assertTrue(
            all(
                "src" not in image
                for image in http.request.call_args.kwargs["body"]["images"]
            )
        )
        overrides = detail["state"]["overrides"]
        overrides["common"]["uk"]["gallery"][0]["alt"] = "Different group metadata"
        changed = await self.call(
            "PUT",
            self.path(channel, group),
            self.version(detail) | {"overrides": overrides},
        )
        different = await self.prepare_media(channel, group, changed)
        self.assertIsNone(different["galleries"][0]["images"][0]["remote_media_id"])
        self.assertEqual(
            different["galleries"][0]["images"][1]["remote_media_id"], "71"
        )
        self.assertEqual(len(await self.rows(ContentMediaModel)), 3)

    async def test_used_file_cannot_be_trashed_but_unused_cache_does_not_pin_it(
        self,
    ) -> None:
        """Сохранённые overrides удерживают файл даже с выключенным экспортом."""
        channel, group, root, detail, images = await self.media_fixture()
        prepared = await self.prepare_media(channel, group, detail)
        await self.call("DELETE", f"/files/items/{images[0]}/", status=409)
        await self.call(
            "POST", self.path(channel, group) + "/disable", self.version(detail)
        )
        await self.call("DELETE", f"/files/items/{images[0]}/", status=409)
        current = await self.call("GET", self.path(channel, group))
        await self.call(
            "PUT", self.path(channel, group), self.version(current) | {"overrides": {}}
        )
        await self.call("DELETE", f"/files/items/{images[0]}/")
        url = prepared["galleries"][0]["images"][0]["url"]
        self.assertEqual((await self.client.get(url)).status_code, 404)
        self.assertEqual(len(await self.rows(ContentMediaModel)), 2)
        await self.call("GET", f"/catalog/items/{root}?locale=uk")

    async def test_concurrent_first_prepare_is_idempotent_and_migration_preserves_files(
        self,
    ) -> None:
        """Резервация отсутствующей строки сериализуется; миграция не публикует существующие Files."""
        channel, group, _, detail, _ = await self.media_fixture()
        results = await asyncio.gather(
            self.prepare_media(channel, group, detail),
            self.prepare_media(channel, group, detail),
            return_exceptions=True,
        )
        for result in results:
            self.assertIsInstance(result, dict, repr(result))
        self.assertEqual(results[0], results[1])
        self.assertEqual(len(await self.rows(ContentMediaModel)), 2)
        files = await self.rows(StoredFileModel)
        async with self.engine.begin() as connection:
            await TenantMigrator().downgrade(
                connection, self.schemas[0], "0011_channels_representations"
            )
            await TenantMigrator().upgrade(connection, self.schemas[0])
        self.assertEqual(await self.rows(ContentMediaModel), [])
        self.assertEqual(await self.rows(StoredFileModel), files)

    async def test_inherited_catalog_images_are_prepared_and_protect_files(
        self,
    ) -> None:
        """После сброса overrides используется галерея Catalog и публичный usage владельца."""
        channel, group, root, detail, images = await self.media_fixture()
        image_id = str(uuid4())
        with patch(
            "src.modules.files.infrastructure.assembly.get_storage_resolver",
            return_value=self.storage,
        ):
            await self.call(
                "PATCH",
                f"/catalog/items/{root}?locale=uk",
                {
                    "gallery": {
                        "images": [
                            {
                                "id": image_id,
                                "file_id": str(images[0]),
                                "position": 0,
                                "alt": "From Catalog",
                            }
                        ],
                        "primary_image_id": image_id,
                    }
                },
            )
        changed = await self.call(
            "PUT", self.path(channel, group), self.version(detail) | {"overrides": {}}
        )
        result = await self.prepare_media(channel, group, changed)
        self.assertEqual(result["galleries"][0]["images"][0]["alt"], "From Catalog")
        self.assertEqual(len(result["galleries"][0]["images"]), 1)
        response = await self.call("DELETE", f"/files/items/{images[0]}/", status=409)
        self.assertEqual(response["detail"]["code"], "file_in_use")

    async def test_catalog_change_during_storage_inspection_does_not_publish_stale_gallery(
        self,
    ) -> None:
        """Вторая фаза замечает изменение Catalog даже без смены ревизии representation."""
        from src.modules.channels.infrastructure.content_media.files import (
            FilesMediaGateway,
        )

        channel, group, root, detail, _ = await self.media_fixture()
        original = FilesMediaGateway.inspect

        async def change(gateway: FilesMediaGateway, files: tuple) -> None:
            """Меняет Catalog после освобождения первой транзакции."""
            await original(gateway, files)
            await self.set_content(root, "uk", "Changed while inspecting storage")

        with patch.object(FilesMediaGateway, "inspect", change):
            await self.call(
                "POST",
                self.path(channel, group) + "/gallery/prepare",
                self.version(detail),
                409,
            )
        self.assertEqual(await self.rows(ContentMediaModel), [])

    async def test_two_transfers_cannot_reserve_same_media_and_stale_result_is_ignored(
        self,
    ) -> None:
        """Один вариант принадлежит одной операции; stale revision не подменяет результат."""
        channel, group, _, detail, _ = await self.media_fixture("woocommerce")
        prepared = await self.prepare_media(channel, group, detail)
        image = prepared["galleries"][0]["images"][0]
        operations = [uuid4(), uuid4()]

        async def reserve(operation: UUID) -> UUID:
            """Использует отдельное соединение и тот же порядок блокировок."""
            async with self.engine.connect() as connection:
                await bind_tenant_schema(connection, self.tenant, self.naming)
                async with UnitOfWork(
                    async_sessionmaker(connection, expire_on_commit=False)
                ) as uow:
                    await BeginMediaTransferHandler(
                        self.runtime(uow).transfers
                    ).execute(
                        BeginMediaTransferCommand(
                            self.tenant,
                            UUID(channel),
                            UUID(group),
                            detail["state"]["revision"],
                            detail["binding_revision"],
                            detail["config_revision"],
                            ((UUID(image["media_id"]), 1),),
                            operation,
                        )
                    )
            return operation

        results = await asyncio.gather(
            *(reserve(operation) for operation in operations), return_exceptions=True
        )
        winners = [result for result in results if isinstance(result, UUID)]
        self.assertEqual(len(winners), 1)
        self.assertEqual(
            sum(isinstance(result, ContentMediaError) for result in results), 1
        )
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant, self.naming)
            async with UnitOfWork(
                async_sessionmaker(connection, expire_on_commit=False)
            ) as uow:
                handler = RecordMediaTransferResultHandler(self.runtime(uow).transfers)
                stale = await handler.execute(
                    RecordMediaTransferResultCommand(
                        UUID(channel),
                        1,
                        "prom.root_group",
                        channel,
                        winners[0],
                        UUID(image["media_id"]),
                        1,
                        "777",
                        None,
                        False,
                    )
                )
                self.assertFalse(stale.applied)
                unknown = await handler.execute(
                    RecordMediaTransferResultCommand(
                        UUID(channel),
                        1,
                        "prom.root_group",
                        channel,
                        winners[0],
                        UUID(image["media_id"]),
                        2,
                        None,
                        "network_timeout",
                        True,
                    )
                )
                self.assertTrue(unknown.applied)
        rows = await self.rows(ContentMediaModel)
        target = next(row for row in rows if row["id"] == UUID(image["media_id"]))
        self.assertEqual(
            (target["transfer_status"], target["remote_media_id"]), ("unknown", None)
        )

    @skipUnless(os.environ.get("TEST_MINIO_ENDPOINT"), "Disposable MinIO required")
    async def test_real_minio_anonymous_http_and_missing_owned_object(self) -> None:
        """Проверяет настоящее приватное хранилище за ограниченным media URL."""
        from src.config import dnk_config
        from src.modules.files.infrastructure.persistence.models.bucket import (
            BucketModel,
        )
        from src.modules.files.application.port.storage import StorageLocation
        from src.modules.files.infrastructure.storage.minio_adapter import (
            MinioStorageAdapter,
        )
        from src.modules.files.infrastructure.storage.resolver import StorageResolver

        channel, group, root, _, _ = await self.fixture()
        identifier = await self.image()
        async with self.sessions() as session:
            await bind_tenant_schema(
                await session.connection(), self.tenant, self.naming
            )
            bucket_id = await session.scalar(
                select(StoredFileModel.bucket_id).where(
                    StoredFileModel.id == identifier
                )
            )
            await session.execute(
                update(BucketModel)
                .where(BucketModel.id == bucket_id)
                .values(name=f"dnk-tenant-{self.tenant.hex}")
            )
            await session.commit()
        location = StorageLocation(
            self.tenant, bucket_id, f"dnk-tenant-{self.tenant.hex}", "minio", "fixture"
        )
        adapter = MinioStorageAdapter(dnk_config.FILES)
        await adapter.ensure_private_bucket(location)
        try:
            await adapter.put(
                location, identifier.hex, BytesIO(PNG), len(PNG), "image/png"
            )
            self.storage = StorageResolver({("minio", "fixture"): lambda: adapter})
            path = self.path(channel, group)
            detail = await self.call("GET", path)
            saved = await self.call(
                "PUT",
                path,
                self.version(detail)
                | {
                    "overrides": {
                        "common": {
                            "uk": {
                                "gallery": [{"file_id": str(identifier), "alt": "Real"}]
                            }
                        }
                    }
                },
            )
            await self.verified(channel)
            enabled = await self.call("POST", path + "/enable", self.version(saved))
            prepared = await self.prepare_media(channel, group, enabled)
            url = prepared["galleries"][0]["images"][0]["url"]
            response = await self.client.get(url, headers={"Cookie": ""})
            self.assertEqual((response.status_code, response.content), (200, PNG))
            await adapter.remove_owned_versions(location, identifier.hex)
            self.assertEqual((await self.client.get(url)).status_code, 404)
        finally:
            await adapter.purge(location)

    async def test_saving_reference_and_trashing_file_are_serialized_in_both_orders(
        self,
    ) -> None:
        """Нельзя сохранить ссылку на корзину или удалить файл после фиксации ссылки."""
        from src.modules.channels.infrastructure.product_representation.repository import (
            SqlAlchemyProductRepresentationRepository,
        )
        from src.modules.files.infrastructure.stored_file.persistence.repository import (
            SqlAlchemyStoredFileRepository,
        )

        channel, group, _, _, _ = await self.fixture()
        path = self.path(channel, group)
        detail = await self.call("GET", path)
        identifier = await self.image()
        body = self.version(detail) | {
            "overrides": {"common": {"uk": {"gallery": [{"file_id": str(identifier)}]}}}
        }
        entered, release = asyncio.Event(), asyncio.Event()
        original = SqlAlchemyProductRepresentationRepository.save

        async def hold_save(
            repository: SqlAlchemyProductRepresentationRepository,
            representation: object,
        ) -> None:
            """Держит Files lock до завершения записи бизнес-ссылки."""
            await original(repository, representation)
            entered.set()
            await release.wait()

        with patch.object(SqlAlchemyProductRepresentationRepository, "save", hold_save):
            saving = asyncio.create_task(
                self.client.put("/api/console" + path, headers=self.headers, json=body)
            )
            await asyncio.wait_for(entered.wait(), 5)
            deleting = asyncio.create_task(
                self.client.delete(
                    f"/api/console/files/items/{identifier}/", headers=self.headers
                )
            )
            await asyncio.sleep(0.05)
            self.assertFalse(deleting.done())
            release.set()
            results = await asyncio.gather(saving, deleting)
        self.assertEqual([result.status_code for result in results], [200, 409])

        detail = await self.call("GET", path)
        identifier = await self.image()
        body = self.version(detail) | {
            "overrides": {"common": {"uk": {"gallery": [{"file_id": str(identifier)}]}}}
        }
        entered, release = asyncio.Event(), asyncio.Event()
        original_file_save = SqlAlchemyStoredFileRepository.save

        async def hold_trash(
            repository: SqlAlchemyStoredFileRepository, file: object
        ) -> None:
            """Держит Files lock после перехода в корзину до commit."""
            await original_file_save(repository, file)
            entered.set()
            await release.wait()

        with patch.object(SqlAlchemyStoredFileRepository, "save", hold_trash):
            deleting = asyncio.create_task(
                self.client.delete(
                    f"/api/console/files/items/{identifier}/", headers=self.headers
                )
            )
            await asyncio.wait_for(entered.wait(), 5)
            saving = asyncio.create_task(
                self.client.put("/api/console" + path, headers=self.headers, json=body)
            )
            await asyncio.sleep(0.05)
            self.assertFalse(saving.done())
            release.set()
            results = await asyncio.gather(deleting, saving)
        self.assertEqual([result.status_code for result in results], [200, 422])
        current = await self.call("GET", path)
        self.assertEqual(current["state"], detail["state"])


def load_tests(loader: TestLoader, tests: TestSuite, pattern: str | None) -> TestSuite:
    """Запускает только новые media-сценарии без повторения унаследованных тестов."""
    return TestSuite(
        ContentMediaPostgresTests(name)
        for name in ContentMediaPostgresTests.__dict__
        if name.startswith("test_")
    )
