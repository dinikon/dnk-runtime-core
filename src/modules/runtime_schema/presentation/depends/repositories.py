from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.runtime_schema.application.bootstrap_tenant_system_schema.ports.repositories import (
    FieldMetadataRepositoryProtocol,
    ObjectMetadataRepositoryProtocol,
    RelationMetadataRepositoryProtocol,
)
from src.modules.runtime_schema.infrastructure.repositories import (
    SqlAlchemyFieldMetadataRepository,
    SqlAlchemyObjectMetadataRepository,
    SqlAlchemyRelationMetadataRepository,
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


def get_relation_metadata_repository(
    uow: UoWDep,
) -> RelationMetadataRepositoryProtocol:
    return SqlAlchemyRelationMetadataRepository(uow.session)


RelationMetadataRepositoryDep = Annotated[
    RelationMetadataRepositoryProtocol,
    Depends(get_relation_metadata_repository),
]

__all__ = [
    "get_object_metadata_repository",
    "ObjectMetadataRepositoryDep",
    "get_field_metadata_repository",
    "FieldMetadataRepositoryDep",
    "get_relation_metadata_repository",
    "RelationMetadataRepositoryDep",
]
