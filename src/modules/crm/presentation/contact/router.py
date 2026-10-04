from fastapi import APIRouter, Depends

from src.modules.crm.presentation.contact.http.controller.create_contact import (
    create_contact,
)
from src.modules.crm.presentation.contact.http.controller.delete_contact import (
    delete_contact,
)
from src.modules.crm.presentation.contact.http.controller.get_contact import get_contact
from src.modules.crm.presentation.contact.http.controller.list_contacts import (
    list_contacts,
)
from src.modules.crm.presentation.contact.http.controller.link_company import (
    link_company,
)
from src.modules.crm.presentation.contact.http.controller.unlink_company import (
    unlink_company,
)
from src.modules.crm.presentation.contact.http.controller.list_companies import (
    list_contact_companies,
)
from src.modules.crm.presentation.contact.http.controller.patch_contact import (
    patch_contact,
)
from src.modules.crm.presentation.contact.http.controller.put_contact import put_contact
from src.modules.crm.presentation.contact.http.response.create_contact import (
    CreateContactResponse,
)
from src.modules.crm.presentation.contact.http.response.get_contact import (
    GetContactResponse,
)
from src.modules.crm.presentation.contact.http.response.list_contacts import (
    ListContactItemResponse,
)
from src.modules.crm.presentation.contact.http.response.list_companies import (
    ListContactCompanyItemResponse,
)
from src.modules.crm.presentation.contact.http.response.patch_contact import (
    PatchContactResponse,
)
from src.modules.crm.presentation.contact.http.response.put_contact import (
    PutContactResponse,
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
    response_model=list[ListContactItemResponse],
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
    response_model=PutContactResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{contact_id}",
    patch_contact,
    methods=["PATCH"],
    response_model=PatchContactResponse,
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
router.add_api_route(
    "/{contact_id}/companies",
    list_contact_companies,
    methods=["GET"],
    response_model=list[ListContactCompanyItemResponse],
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{contact_id}/companies/{company_id}",
    link_company,
    methods=["PUT"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{contact_id}/companies/{company_id}",
    unlink_company,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
