from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config import dnk_config

control_plane_bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="ControlPlaneBearer",
    description="ControlPlane API key in format: Bearer <API_KEY>",
)


def get_control_plane_api_key() -> str:
    """Возвращает API key control plane из конфигурации."""

    return dnk_config.CONTROL_PLANE_API_KEY


ControlPlaneApiKeyDep = Annotated[str, Depends(get_control_plane_api_key)]


async def authorize_control_plane_request(
    control_plane_api_key: ControlPlaneApiKeyDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(control_plane_bearer_scheme),
    ] = None,
) -> None:
    """Проверяет Bearer API key для admin/control-plane endpoints."""
    if not control_plane_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Control plane API key is not configured.",
        )

    if (
        credentials is None
        or credentials.scheme != "Bearer"
        or not credentials.credentials
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not secrets.compare_digest(credentials.credentials, control_plane_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
            headers={"WWW-Authenticate": "Bearer"},
        )


AdminCreateTenantAuthorizationDep = Annotated[
    None,
    Depends(authorize_control_plane_request),
]


__all__ = [
    "AdminCreateTenantAuthorizationDep",
    "ControlPlaneApiKeyDep",
    "authorize_control_plane_request",
    "get_control_plane_api_key",
]
