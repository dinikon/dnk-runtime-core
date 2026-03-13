from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.modules.runtime_record import (
    FindRuntimeRecordQuery,
    GetRuntimeRecordQuery,
    UpsertRuntimeRecordCommand,
)
from src.modules.runtime_record.infrastructure.factory import build_runtime_record_storage
from src.modules.runtime_schema.application.sync_tenant_system_schema.dto import (
    SyncTenantSystemSchemaCommandDTO,
)
from src.modules.runtime_schema.infrastructure.factory import build_ddl_orchestrator
from src.modules.shared import EntityIdVO
from src.modules.shorter.domain.link.entity import LinkEntity
from src.modules.shorter.domain.template.entity import TemplateEntity
from src.modules.shorter.domain.template.value_object import (
    TemplateEntityTypeVO,
    TemplateTargetModuleTypeVO,
)
from src.modules.shorter.infrastructure.link.repositories import (
    RuntimeRecordLinkRepository,
)
from src.modules.shorter.infrastructure.template.repositories import (
    RuntimeRecordTemplateRepository,
)
from src.modules.tenancy.infrastructure.persistence.data_source import (
    TenantDataSourceModel,
)
from test.runtime_schema_test_utils import sqlite_session


async def _bootstrap_runtime_schema(
    *,
    session,
    tenant_id: UUID,
    data_source_id: UUID,
    schema: str,
) -> None:
    session.add(
        TenantDataSourceModel(
            id=data_source_id,
            tenant_id=tenant_id,
            type="sqlite",
            is_remote=False,
            dsn=None,
            schema=schema,
        )
    )
    await session.flush()
    orchestrator = build_ddl_orchestrator(session=session)
    await orchestrator.sync_tenant_system_schema(
        SyncTenantSystemSchemaCommandDTO(
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            schema=schema,
        )
    )


def _as_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise AssertionError(f"expected datetime value, got {type(value)!r}")


class TestRuntimeRecordStorageForShorter(unittest.IsolatedAsyncioTestCase):
    async def test_upsert_get_and_find_by_fields(self) -> None:
        tenant_id = uuid4()
        data_source_id = uuid4()
        schema = "tenant_shorter_storage"
        now = datetime(2026, 3, 12, 12, 0, tzinfo=UTC)
        link_id = uuid4()

        async with sqlite_session() as session:
            await _bootstrap_runtime_schema(
                session=session,
                tenant_id=tenant_id,
                data_source_id=data_source_id,
                schema=schema,
            )
            runtime_storage = build_runtime_record_storage(session=session)

            await runtime_storage.upsert_record(
                UpsertRuntimeRecordCommand(
                    tenant_id=tenant_id,
                    object_name_singular="shorter_link",
                    record_id=link_id,
                    values={
                        "created_at": now,
                        "domain_id": tenant_id,
                        "code": "ABCD1234",
                    },
                )
            )

            payload = await runtime_storage.get_record(
                GetRuntimeRecordQuery(
                    tenant_id=tenant_id,
                    object_name_singular="shorter_link",
                    record_id=link_id,
                )
            )
            self.assertIsNotNone(payload)
            assert payload is not None
            self.assertEqual(payload.record_id, link_id)
            self.assertEqual(payload.system_values["code"], "ABCD1234")
            self.assertEqual(
                _as_datetime(payload.system_values["created_at"]),
                now,
            )

            found = await runtime_storage.get_record_by_fields(
                FindRuntimeRecordQuery(
                    tenant_id=tenant_id,
                    object_name_singular="shorter_link",
                    filters={
                        "domain_id": tenant_id,
                        "code": "ABCD1234",
                    },
                )
            )
            self.assertIsNotNone(found)
            assert found is not None
            self.assertEqual(found.record_id, link_id)


class TestShorterRuntimeRecordRepositories(unittest.IsolatedAsyncioTestCase):
    async def test_link_and_template_repositories_read_write(self) -> None:
        tenant_id = uuid4()
        data_source_id = uuid4()
        schema = "tenant_shorter_repositories"
        now = datetime(2026, 3, 12, 12, 0, tzinfo=UTC)

        async with sqlite_session() as session:
            await _bootstrap_runtime_schema(
                session=session,
                tenant_id=tenant_id,
                data_source_id=data_source_id,
                schema=schema,
            )
            runtime_storage = build_runtime_record_storage(session=session)

            link_repository = RuntimeRecordLinkRepository(runtime_storage)
            template_repository = RuntimeRecordTemplateRepository(
                tenant_id=EntityIdVO.from_value(tenant_id),
                runtime_record_storage=runtime_storage,
            )

            link = LinkEntity.create(
                domain_id=EntityIdVO.from_value(tenant_id),
                code="XYZA7788",
                created_at=now,
            )
            await link_repository.save(link)

            exists = await link_repository.exists_by_domain_and_code(
                domain_id=EntityIdVO.from_value(tenant_id),
                code="XYZA7788",
            )
            self.assertTrue(exists)

            loaded_link = await link_repository.get_by_id(
                domain_id=EntityIdVO.from_value(tenant_id),
                link_id=link.id,
            )
            self.assertIsNotNone(loaded_link)
            assert loaded_link is not None
            self.assertEqual(loaded_link.id, link.id)
            self.assertEqual(loaded_link.code, link.code)
            self.assertEqual(loaded_link.domain_id, link.domain_id)
            self.assertEqual(loaded_link.created_at, link.created_at)

            template = TemplateEntity.create(
                user_id=EntityIdVO.from_value(uuid4()),
                target_module=TemplateTargetModuleTypeVO.SHORTER,
                target_entity=TemplateEntityTypeVO.REDIRECT,
                target_entity_id=EntityIdVO.from_value(uuid4()),
                default_code=link.id,
                created_at=now,
            )
            await template_repository.save(template)
            loaded_template = await template_repository.get_by_id(
                template_id=template.id,
            )

            self.assertIsNotNone(loaded_template)
            assert loaded_template is not None
            self.assertEqual(loaded_template.id, template.id)
            self.assertEqual(loaded_template.created_by, template.created_by)
            self.assertEqual(loaded_template.default_code, template.default_code)
            self.assertEqual(loaded_template.target_module, template.target_module)
            self.assertEqual(loaded_template.target_entity, template.target_entity)
            self.assertEqual(loaded_template.target_entity_id, template.target_entity_id)
            self.assertEqual(loaded_template.created_at, template.created_at)
            self.assertEqual(loaded_template.updated_at, template.updated_at)


if __name__ == "__main__":
    unittest.main()
