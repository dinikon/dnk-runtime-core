"""Host-only browser binding and session-bound CSRF tokens for JSON mutations."""

import hashlib
import secrets

from fastapi import HTTPException, Request, Response

from src.config import dnk_config
from src.modules.shared.presentation.tokens.depends import TokenManagerDep
from src.modules.shared.presentation.http.host import extract_request_host

FLOW_COOKIE = "dnk_auth_flow"


def digest(value):
    return hashlib.sha256((value or "").encode()).hexdigest()


def secure_cookie():
    return not dnk_config.AUTH.allow_insecure_http


def browser_session(request):
    return request.cookies.get(dnk_config.AUTH.session_cookie_name)


def flow_cookie(request):
    return request.cookies.get(FLOW_COOKIE)


def set_session_cookie(response, session):
    response.set_cookie(
        dnk_config.AUTH.session_cookie_name,
        session.token,
        max_age=dnk_config.AUTH.session_ttl_seconds,
        secure=secure_cookie(),
        httponly=True,
        samesite="lax",
        path="/",
    )


async def issue_csrf(request: Request, response: Response, tokens: TokenManagerDep):
    host = extract_request_host(request)
    flow = flow_cookie(request) or secrets.token_urlsafe(32)
    token = secrets.token_urlsafe(32)
    await tokens.set_token(
        prefix="csrf",
        suffix=host,
        token=token,
        body={"flow": digest(flow), "session": digest(browser_session(request))},
        ttl=900,
    )
    response.set_cookie(
        FLOW_COOKIE,
        flow,
        max_age=86400,
        secure=secure_cookie(),
        httponly=True,
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"csrf_token": token}


async def require_csrf(request: Request, tokens: TokenManagerDep):
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    host = extract_request_host(request)
    scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
    expected = f"{scheme}://{request.url.netloc}"
    if request.headers.get("origin") != expected:
        raise HTTPException(403, "Request origin does not match this workspace.")
    supplied = request.headers.get("x-csrf-token")
    flow = flow_cookie(request)
    if not supplied or not flow:
        raise HTTPException(403, "CSRF token required.")
    record = await tokens.get_token(prefix="csrf", suffix=host, token=supplied)
    if (
        not record
        or not secrets.compare_digest(str(record.get("flow", "")), digest(flow))
        or not secrets.compare_digest(
            str(record.get("session", "")), digest(browser_session(request))
        )
    ):
        raise HTTPException(403, "CSRF token is invalid or expired.")
