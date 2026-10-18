from fastapi import Depends
from src.modules.identity.application.cloud.service.connection import (
    CloudConnectionService,
)
from src.modules.identity.presentation.cloud.providers import CloudConnectionsDep
from typing import Annotated


def get_cloud_connection(connections: CloudConnectionsDep) -> CloudConnectionService:
    return CloudConnectionService(connections=connections)


CloudConnectionServiceDep = Annotated[
    CloudConnectionService, Depends(get_cloud_connection)
]
