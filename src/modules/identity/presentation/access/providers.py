from fastapi import Depends
from src.config import dnk_config
from src.modules.control_plane.infrastructure.services import AccessProjectionWriter
from src.modules.identity.application.access.port.repository import (
    AccessRepositoryProtocol,
)
from src.modules.identity.application.cloud.port.cloud import AccessProjectionWriterPort
from src.modules.identity.infrastructure.access.persistence.repository import (
    AccessRepository,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from typing import Annotated


def get_access_repository(uow: UoWDep) -> AccessRepositoryProtocol:
    return AccessRepository(uow.session, TenantSchemaNaming(dnk_config.SCHEMA_PREFIX))


AccessRepositoryDep = Annotated[
    AccessRepositoryProtocol, Depends(get_access_repository)
]


def get_access_projections(uow: UoWDep) -> AccessProjectionWriterPort:
    return AccessProjectionWriter(uow.session)


AccessProjectionsDep = Annotated[
    AccessProjectionWriterPort, Depends(get_access_projections)
]
