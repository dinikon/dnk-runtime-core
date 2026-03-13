from typing import Annotated

from fastapi import Depends, Request

from src.modules.shared.http.host import extract_request_host


def get_request_host(request: Request) -> str:
    return extract_request_host(request)


RequestHostDep = Annotated[str, Depends(get_request_host)]
