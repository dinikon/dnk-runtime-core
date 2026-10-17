from fastapi import Request
from src.modules.shared.application.network import host as host_utils


def extract_request_host(request: Request) -> str:
    """Достает host из FastAPI request и нормализует его."""
    raw_host = request.headers.get("host", "")
    return host_utils.normalize_host(raw_host)
