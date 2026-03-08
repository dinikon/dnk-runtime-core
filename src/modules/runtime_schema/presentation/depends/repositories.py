from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.ports.repositories import (
    FieldMetadataRepositoryProtocol,
    ObjectMetadataRepositoryProtocol,
)
from src.modules.runtime_schema.infrastructure.repositories import (
    SqlAlchemyFieldMetadataRepository,
    SqlAlchemyObjectMetadataRepository,
)
from src.modules.shared.depends.uow import UoWDep


def get_object_metadata_repository(
    uow: UoWDep,
) -> ObjectMetadataRepositoryProtocol:
    return SqlAlchemyObjectMetadataRepository(uow.session)


ObjectMetadataRepositoryDep = Annotated[
    ObjectMetadataRepositoryProtocol,
    Depends(get_object_metadata_repository),
]


def get_field_metadata_repository(
    uow: UoWDep,
) -> FieldMetadataRepositoryProtocol:
    return SqlAlchemyFieldMetadataRepository(uow.session)


FieldMetadataRepositoryDep = Annotated[
    FieldMetadataRepositoryProtocol,
    Depends(get_field_metadata_repository),
]

__all__ = [
    "get_object_metadata_repository",
    "ObjectMetadataRepositoryDep",
    "get_field_metadata_repository",
    "FieldMetadataRepositoryDep",
]
