from typing import Annotated

from fastapi import Depends, Request

from src.modules.shared.presentation.http.host import extract_request_host


def get_request_host(request: Request) -> str:
    """Возвращает нормализованный host текущего request."""

    return extract_request_host(request)


RequestHostDep = Annotated[str, Depends(get_request_host)]
