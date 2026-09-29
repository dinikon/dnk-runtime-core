from fastapi import APIRouter, Depends

from src.modules.crm.presentation.contact.http.controller import create_contact
from src.modules.crm.presentation.contact.http.response import CreateContactResponse
from src.modules.identity.presentation.http.csrf import require_csrf
from src.modules.shared.presentation.identity_context.depends import (
    require_authenticated_request_context,
)

router = APIRouter(prefix="/crm/contacts", tags=["crm-contacts"])
router.add_api_route(
    "",
    create_contact,
    methods=["POST"],
    status_code=201,
    response_model=CreateContactResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
