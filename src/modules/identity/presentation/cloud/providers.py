from fastapi import Depends, Request
from src.config import dnk_config
from src.modules.control_plane.infrastructure.services import CloudConnectionReader
from src.modules.identity.application.cloud.port.cloud import CloudConnectionReaderPort
from src.modules.identity.application.cloud.port.oidc import OidcClientPort
from src.modules.identity.infrastructure.cloud.oidc_client import OidcClient
from src.modules.shared.presentation.persistence.depends import UoWDep
from typing import Annotated

_oidc_clients: dict[str, OidcClientPort] = {}


def get_oidc_client(request: Request) -> OidcClientPort:
    origin = dnk_config.CONTROL_PLANE.public_origin
    oidc = getattr(request.app.state, "oidc_client", None) or _oidc_clients.get(origin)
    if oidc is None:
        oidc = _oidc_clients[origin] = OidcClient(origin)
    return oidc


OidcClientDep = Annotated[OidcClientPort, Depends(get_oidc_client)]


def get_cloud_connections(uow: UoWDep) -> CloudConnectionReaderPort:
    return CloudConnectionReader(uow.session)


CloudConnectionsDep = Annotated[
    CloudConnectionReaderPort, Depends(get_cloud_connections)
]
