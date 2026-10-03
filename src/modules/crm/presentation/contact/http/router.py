from fastapi import APIRouter, Depends

from src.modules.crm.presentation.contact.http.controller import (
    create_contact,
    delete_contact,
    get_contact,
    list_contacts,
    patch_contact,
    put_contact,
)
from src.modules.crm.presentation.contact.http.response import (
    CreateContactResponse,
    GetContactResponse,
    UpdateContactResponse,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)

router = APIRouter(prefix="/crm/contacts", tags=["crm-contacts"])
router.add_api_route(
    "",
    list_contacts,
    methods=["GET"],
    response_model=list[GetContactResponse],
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{contact_id}",
    get_contact,
    methods=["GET"],
    response_model=GetContactResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
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
router.add_api_route(
    "/{contact_id}",
    put_contact,
    methods=["PUT"],
    response_model=UpdateContactResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{contact_id}",
    patch_contact,
    methods=["PATCH"],
    response_model=UpdateContactResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{contact_id}",
    delete_contact,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
