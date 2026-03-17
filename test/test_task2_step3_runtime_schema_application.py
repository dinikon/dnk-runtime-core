from __future__ import annotations

import unittest
from uuid import UUID, uuid4

from src.modules.runtime_schema.application.commands import (
    CreateDataSourceCommand,
    DeleteDataSourceCommand,
)
from src.modules.runtime_schema.application.queries import (
    GetObjectRuntimeSchemaQuery,
    ListObjectFieldDefinitionsQuery,
)
from src.modules.runtime_schema.application.use_cases import (
    CreateDataSourceUseCase,
    DeleteDataSourceUseCase,
    GetObjectRuntimeSchemaUseCase,
    ListObjectFieldDefinitionsUseCase,
)
from src.modules.runtime_schema.domain import (
    DataSource,
    DataSourceNotFoundError,
    FieldMetadata,
    FieldType,
    ObjectMetadata,
    ObjectMetadataNotFoundError,
    ObjectOwnershipKind,
)


class FakeUoW:
    def __init__(self) -> None:
        self.session = None
        self.entered = False
        self.exited = False
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self) -> "FakeUoW":
        self.entered = True
        self.session = object()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.exited = True
        if exc_type:
            await self.rollback()
        self.session = None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeDataSourceRepository:
    def __init__(self, *, fail_on_add: bool = False) -> None:
        self._items: dict[UUID, DataSource] = {}
        self.fail_on_add = fail_on_add

    async def add(self, data_source: DataSource) -> None:
        if self.fail_on_add:
            raise RuntimeError("write failed")
        self._items[data_source.id] = data_source

    async def get_by_id(self, data_source_id: UUID) -> DataSource | None:
        return self._items.get(data_source_id)

    async def list_by_tenant_id(self, tenant_id: UUID) -> tuple[DataSource, ...]:
        return tuple(item for item in self._items.values() if item.tenant_id == tenant_id)

    async def delete_by_id(self, data_source_id: UUID) -> bool:
        return self._items.pop(data_source_id, None) is not None


class FakeObjectMetadataRepository:
    def __init__(self, items: tuple[ObjectMetadata, ...] = ()) -> None:
        self._items: dict[UUID, ObjectMetadata] = {item.id: item for item in items}

    async def add(self, object_metadata: ObjectMetadata) -> None:
        self._items[object_metadata.id] = object_metadata

    async def get_by_id(self, object_metadata_id: UUID) -> ObjectMetadata | None:
        return self._items.get(object_metadata_id)

    async def get_by_name(
        self,
        *,
        tenant_id: UUID,
        name_singular: str,
    ) -> ObjectMetadata | None:
        normalized = name_singular.strip()
        for item in self._items.values():
            if item.tenant_id == tenant_id and item.name_singular == normalized:
                return item
        return None

    async def list_by_tenant_id(self, tenant_id: UUID) -> tuple[ObjectMetadata, ...]:
        return tuple(item for item in self._items.values() if item.tenant_id == tenant_id)


class FakeFieldMetadataRepository:
    def __init__(self, items: tuple[FieldMetadata, ...] = ()) -> None:
        self._items: dict[UUID, FieldMetadata] = {item.id: item for item in items}

    async def add(self, field_metadata: FieldMetadata) -> None:
        self._items[field_metadata.id] = field_metadata

    async def get_by_id(self, field_metadata_id: UUID) -> FieldMetadata | None:
        return self._items.get(field_metadata_id)

    async def get_by_name(
        self,
        *,
        object_metadata_id: UUID,
        name: str,
    ) -> FieldMetadata | None:
        for item in self._items.values():
            if item.object_metadata_id == object_metadata_id and item.name == name:
                return item
        return None

    async def list_by_object_metadata_id(
        self,
        object_metadata_id: UUID,
    ) -> tuple[FieldMetadata, ...]:
        return tuple(
            item
            for item in self._items.values()
            if item.object_metadata_id == object_metadata_id
        )

    async def delete_by_id(self, field_metadata_id: UUID) -> bool:
        return self._items.pop(field_metadata_id, None) is not None


class TestRuntimeSchemaApplicationStep3(unittest.IsolatedAsyncioTestCase):
    async def test_create_data_source_use_case_commits(self) -> None:
        uow = FakeUoW()
        repository = FakeDataSourceRepository()
        use_case = CreateDataSourceUseCase(
            uow=uow,
            data_source_repository=repository,
        )

        result = await use_case.execute(
            CreateDataSourceCommand(tenant_id=uuid4())
        )

        self.assertTrue(uow.entered)
        self.assertTrue(uow.exited)
        self.assertEqual(uow.commits, 1)
        self.assertEqual(uow.rollbacks, 0)
        self.assertEqual(result.source_type, "postgresql")
        self.assertEqual(len(repository._items), 1)

    async def test_create_data_source_use_case_rolls_back_on_error(self) -> None:
        uow = FakeUoW()
        repository = FakeDataSourceRepository(fail_on_add=True)
        use_case = CreateDataSourceUseCase(
            uow=uow,
            data_source_repository=repository,
        )

        with self.assertRaises(RuntimeError):
            await use_case.execute(CreateDataSourceCommand(tenant_id=uuid4()))

        self.assertTrue(uow.entered)
        self.assertTrue(uow.exited)
        self.assertEqual(uow.commits, 0)
        self.assertEqual(uow.rollbacks, 1)

    async def test_delete_data_source_use_case_commits(self) -> None:
        uow = FakeUoW()
        repository = FakeDataSourceRepository()
        existing = DataSource.create(tenant_id=uuid4())
        await repository.add(existing)

        use_case = DeleteDataSourceUseCase(
            uow=uow,
            data_source_repository=repository,
        )
        result = await use_case.execute(
            DeleteDataSourceCommand(data_source_id=existing.id)
        )

        self.assertTrue(result.deleted)
        self.assertEqual(result.data_source_id, existing.id)
        self.assertEqual(uow.commits, 1)
        self.assertEqual(uow.rollbacks, 0)
        self.assertEqual(len(repository._items), 0)

    async def test_delete_data_source_use_case_rolls_back_when_not_found(self) -> None:
        uow = FakeUoW()
        repository = FakeDataSourceRepository()
        use_case = DeleteDataSourceUseCase(
            uow=uow,
            data_source_repository=repository,
        )

        with self.assertRaises(DataSourceNotFoundError):
            await use_case.execute(DeleteDataSourceCommand(data_source_id=uuid4()))

        self.assertEqual(uow.commits, 0)
        self.assertEqual(uow.rollbacks, 1)

    async def test_get_object_runtime_schema_use_case_returns_object_and_fields(
        self,
    ) -> None:
        tenant_id = uuid4()
        object_metadata = ObjectMetadata.create(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            name_singular="contact",
            name_plural="contacts",
            label_singular="Contact",
            label_plural="Contacts",
            ownership_kind=ObjectOwnershipKind.MODULE,
            allows_custom_fields=True,
        )
        field_one = FieldMetadata.create(
            object_metadata_id=object_metadata.id,
            tenant_id=tenant_id,
            field_type=FieldType.STRING,
            name="telegram",
            label="Telegram",
        )
        field_two = FieldMetadata.create(
            object_metadata_id=object_metadata.id,
            tenant_id=tenant_id,
            field_type=FieldType.BOOLEAN,
            name="is_vip",
            label="VIP",
        )

        use_case = GetObjectRuntimeSchemaUseCase(
            object_metadata_repository=FakeObjectMetadataRepository((object_metadata,)),
            field_metadata_repository=FakeFieldMetadataRepository((field_one, field_two)),
        )

        result = await use_case.execute(
            GetObjectRuntimeSchemaQuery(
                tenant_id=tenant_id,
                name_singular="contact",
            )
        )

        self.assertEqual(result.object_metadata.id, object_metadata.id)
        self.assertEqual(len(result.fields), 2)
        self.assertEqual({item.name for item in result.fields}, {"telegram", "is_vip"})

    async def test_get_object_runtime_schema_use_case_raises_when_not_found(
        self,
    ) -> None:
        use_case = GetObjectRuntimeSchemaUseCase(
            object_metadata_repository=FakeObjectMetadataRepository(),
            field_metadata_repository=FakeFieldMetadataRepository(),
        )

        with self.assertRaises(ObjectMetadataNotFoundError):
            await use_case.execute(
                GetObjectRuntimeSchemaQuery(
                    tenant_id=uuid4(),
                    name_singular="contact",
                )
            )

    async def test_list_object_field_definitions_use_case_returns_fields(self) -> None:
        tenant_id = uuid4()
        object_metadata = ObjectMetadata.create(
            tenant_id=tenant_id,
            data_source_id=uuid4(),
            name_singular="company",
            name_plural="companies",
            label_singular="Company",
            label_plural="Companies",
            ownership_kind=ObjectOwnershipKind.MODULE,
            allows_custom_fields=True,
        )
        field = FieldMetadata.create(
            object_metadata_id=object_metadata.id,
            tenant_id=tenant_id,
            field_type=FieldType.SELECT,
            name="category",
            label="Category",
            options=("vendor", "partner"),
        )

        use_case = ListObjectFieldDefinitionsUseCase(
            object_metadata_repository=FakeObjectMetadataRepository((object_metadata,)),
            field_metadata_repository=FakeFieldMetadataRepository((field,)),
        )

        result = await use_case.execute(
            ListObjectFieldDefinitionsQuery(object_metadata_id=object_metadata.id)
        )

        self.assertEqual(result.object_metadata_id, object_metadata.id)
        self.assertEqual(len(result.fields), 1)
        self.assertEqual(result.fields[0].name, "category")

    async def test_list_object_field_definitions_use_case_raises_when_not_found(
        self,
    ) -> None:
        use_case = ListObjectFieldDefinitionsUseCase(
            object_metadata_repository=FakeObjectMetadataRepository(),
            field_metadata_repository=FakeFieldMetadataRepository(),
        )

        with self.assertRaises(ObjectMetadataNotFoundError):
            await use_case.execute(
                ListObjectFieldDefinitionsQuery(object_metadata_id=uuid4())
            )


if __name__ == "__main__":
    unittest.main()
