import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from src.config import dnk_config
from src.modules.control_plane.application.contracts import (
    AttemptResponse,
    ProvisioningCommand,
    StatusResponse,
    DomainReadiness,
    DeletionResponse,
    DeletionCapability,
)
from src.modules.control_plane.infrastructure.readiness import (
    instance_status,
    probe_hostname,
    tenant_ready,
)
from src.modules.control_plane.application.services import (
    AcceptProvisioningCommand,
    ProvisioningConflict,
)
from src.modules.control_plane.infrastructure.services import ProvisioningRepository
from src.modules.control_plane.infrastructure.tenancy_adapter import TenancyAdapter
from src.modules.shared.presentation.http.host import extract_request_host
from src.modules.shared.presentation.persistence.depends import UoWDep

router = APIRouter()


def settings(request: Request):
    return getattr(
        request.app.state, "control_plane_settings", dnk_config.CONTROL_PLANE
    )


async def require_management(request: Request):
    if not settings(request).enabled:
        raise HTTPException(503, "Integration is disabled")
    if getattr(request.state, "control_plane_trusted", False) is not True:
        raise HTTPException(403, "Management identity is required")


@router.get(
    "/internal/v1/status/",
    response_model=StatusResponse,
    dependencies=[Depends(require_management)],
)
async def status(request: Request, uow: UoWDep):
    config = settings(request)
    try:
        async with asyncio.timeout(4):
            return await instance_status(uow.session, config)
    except Exception:
        await uow.rollback()
        return StatusResponse(
            ready=False,
            domains=[
                DomainReadiness(base_domain=zone, routing_ready=False, tls_ready=False)
                for zone in config.allowed_base_domains
            ],
        )


@router.post(
    "/internal/v1/tenant-provisioning/",
    response_model=AttemptResponse,
    status_code=202,
    dependencies=[Depends(require_management)],
)
async def provision(
    request: Request, uow: UoWDep, idempotency_key: str = Header(default="")
):
    # Manual parsing keeps FastAPI validation responses from echoing secret inputs.
    try:
        content_length = int(request.headers.get("content-length", "0"))
    except ValueError:
        raise HTTPException(400, "Invalid content length") from None
    if content_length > 65536:
        raise HTTPException(413, "Command is too large")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 65536:
            raise HTTPException(413, "Command is too large")
    try:
        command = ProvisioningCommand.model_validate_json(body)
        repository = ProvisioningRepository(
            uow.session,
            settings(request),
            TenancyAdapter(uow.session, dnk_config.SCHEMA_PREFIX),
        )
        result = await AcceptProvisioningCommand(repository, settings(request))(
            command, idempotency_key
        )
        # Explicit durable acceptance BEFORE any response can leave the application.
        await uow.commit()
        return result
    except (ValueError, ValidationError):
        raise HTTPException(422, "Invalid provisioning command") from None
    except (ProvisioningConflict, IntegrityError):
        await uow.rollback()
        raise HTTPException(
            409, "Provisioning command conflicts with durable state"
        ) from None


@router.get(
    "/internal/v1/tenant-provisioning/{attempt_id}/",
    response_model=AttemptResponse,
    dependencies=[Depends(require_management)],
)
async def lookup(attempt_id: UUID, request: Request, uow: UoWDep):
    result = await ProvisioningRepository(uow.session, settings(request)).lookup(
        attempt_id
    )
    if result is None:
        raise HTTPException(404, "Attempt not found")
    return result


@router.get("/internal/v1/metrics/", dependencies=[Depends(require_management)])
async def metrics(request: Request, uow: UoWDep):
    from src.modules.control_plane.infrastructure.metrics import render_metrics

    return Response(
        await render_metrics(uow.session, settings(request)),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/.well-known/dnk/instance-routing")
async def instance_routing(request: Request):
    config, hostname = settings(request), extract_request_host(request)
    if not config.enabled or hostname not in {
        probe_hostname(config, zone) for zone in config.allowed_base_domains
    }:
        raise HTTPException(404, "Not found")
    return JSONResponse(
        {"instance_id": str(config.instance_id), "hostname": hostname},
        headers={"Cache-Control": "no-store"},
    )


@router.get("/.well-known/dnk/tenant-ready")
async def public_ready(request: Request, uow: UoWDep):
    config = settings(request)
    if not config.enabled:
        raise HTTPException(503, "Integration is disabled")
    try:
        result = await tenant_ready(
            uow.session, config, dnk_config.SCHEMA_PREFIX, extract_request_host(request)
        )
    except Exception:
        await uow.rollback()
        raise HTTPException(503, "Installation is not ready") from None
    if result is None:
        raise HTTPException(404, "Not found")
    if result is False:
        raise HTTPException(503, "Installation is not ready")
    try:
        async with asyncio.timeout(4):
            instance = await instance_status(uow.session, config)
        if not instance.ready:
            raise HTTPException(503, "Local installation services are not ready")
    except HTTPException:
        raise
    except Exception:
        await uow.rollback()
        raise HTTPException(503, "Local installation services are not ready") from None
    return JSONResponse(result, headers={"Cache-Control": "no-store"})


def deletion_repository(request, session):
    from src.modules.control_plane.infrastructure.deletion import DeletionRepository

    return DeletionRepository(session, settings(request), dnk_config.SCHEMA_PREFIX)


async def deletion_body(request, limit):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > limit:
            raise HTTPException(413, "Command is too large")
    return body


@router.get(
    "/internal/v1/tenants/{tenant_id}/deletion-capability/{user_id}/",
    response_model=DeletionCapability,
    dependencies=[Depends(require_management)],
)
async def deletion_capability(
    tenant_id: UUID, user_id: UUID, request: Request, uow: UoWDep
):
    from src.modules.control_plane.application.contracts import DeletionCapability

    allowed = await deletion_repository(request, uow.session).admin(tenant_id, user_id)
    return DeletionCapability(
        can_delete=allowed, reason=None if allowed else "administrator_required"
    )


@router.post(
    "/internal/v1/tenant-deletions/",
    response_model=DeletionResponse,
    status_code=202,
    dependencies=[Depends(require_management)],
)
async def accept_deletion(
    request: Request, uow: UoWDep, idempotency_key: str = Header(default="")
):
    from src.modules.control_plane.application.contracts import DeletionCommand
    from src.modules.control_plane.infrastructure.deletion import DeletionError

    try:
        body = await deletion_body(request, 8192)
        command = DeletionCommand.model_validate_json(body)
        if idempotency_key != str(command.operation_id):
            raise ValueError
        result = await deletion_repository(request, uow.session).accept(command)
        await uow.commit()
        return result
    except (ValueError, ValidationError):
        raise HTTPException(422, "Invalid deletion command") from None
    except DeletionError as exc:
        await uow.rollback()
        raise HTTPException(exc.status, exc.code) from None
    except IntegrityError:
        await uow.rollback()
        raise HTTPException(409, "command_conflict") from None


@router.get(
    "/internal/v1/tenant-deletions/{operation_id}/",
    response_model=DeletionResponse,
    dependencies=[Depends(require_management)],
)
async def lookup_deletion(operation_id: UUID, request: Request, uow: UoWDep):
    result = await deletion_repository(request, uow.session).lookup(operation_id)
    if result is None:
        raise HTTPException(404, "deletion_not_found")
    return result


@router.post(
    "/internal/v1/tenant-deletions/{operation_id}/purge/",
    response_model=DeletionResponse,
    status_code=202,
    dependencies=[Depends(require_management)],
)
async def purge_deletion(
    operation_id: UUID,
    request: Request,
    uow: UoWDep,
    idempotency_key: str = Header(default=""),
):
    from src.modules.control_plane.application.contracts import PurgeCommand
    from src.modules.control_plane.infrastructure.deletion import DeletionError

    try:
        body = await deletion_body(request, 4096)
        if idempotency_key != str(operation_id):
            raise ValueError
        command = PurgeCommand.model_validate_json(body)
        result = await deletion_repository(request, uow.session).request_purge(
            operation_id, command
        )
        await uow.commit()
        return result
    except (ValueError, ValidationError):
        raise HTTPException(422, "Invalid purge command") from None
    except DeletionError as exc:
        await uow.rollback()
        raise HTTPException(exc.status, exc.code) from None
