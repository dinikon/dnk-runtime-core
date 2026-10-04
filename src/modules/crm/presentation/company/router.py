from fastapi import APIRouter, Depends

from src.modules.crm.presentation.company.http.controller.create_company import (
    create_company,
)
from src.modules.crm.presentation.company.http.controller.delete_company import (
    delete_company,
)
from src.modules.crm.presentation.company.http.controller.get_company import get_company
from src.modules.crm.presentation.company.http.controller.list_companies import (
    list_companies,
)
from src.modules.crm.presentation.company.http.controller.link_contact import (
    link_contact,
)
from src.modules.crm.presentation.company.http.controller.unlink_contact import (
    unlink_contact,
)
from src.modules.crm.presentation.company.http.controller.list_contacts import (
    list_company_contacts,
)
from src.modules.crm.presentation.company.http.controller.patch_company import (
    patch_company,
)
from src.modules.crm.presentation.company.http.controller.put_company import put_company
from src.modules.crm.presentation.company.http.response.create_company import (
    CreateCompanyResponse,
)
from src.modules.crm.presentation.company.http.response.get_company import (
    GetCompanyResponse,
)
from src.modules.crm.presentation.company.http.response.list_companies import (
    ListCompanyItemResponse,
)
from src.modules.crm.presentation.company.http.response.list_contacts import (
    ListCompanyContactItemResponse,
)
from src.modules.crm.presentation.company.http.response.patch_company import (
    PatchCompanyResponse,
)
from src.modules.crm.presentation.company.http.response.put_company import (
    PutCompanyResponse,
)
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.http.csrf import require_csrf

router = APIRouter(prefix="/crm/companies", tags=["crm-companies"])
router.add_api_route(
    "",
    list_companies,
    methods=["GET"],
    response_model=list[ListCompanyItemResponse],
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{company_id}",
    get_company,
    methods=["GET"],
    response_model=GetCompanyResponse,
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "",
    create_company,
    methods=["POST"],
    status_code=201,
    response_model=CreateCompanyResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{company_id}",
    put_company,
    methods=["PUT"],
    response_model=PutCompanyResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{company_id}",
    patch_company,
    methods=["PATCH"],
    response_model=PatchCompanyResponse,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{company_id}",
    delete_company,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{company_id}/contacts",
    list_company_contacts,
    methods=["GET"],
    response_model=list[ListCompanyContactItemResponse],
    dependencies=[Depends(require_authenticated_request_context)],
)
router.add_api_route(
    "/{company_id}/contacts/{contact_id}",
    link_contact,
    methods=["PUT"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
router.add_api_route(
    "/{company_id}/contacts/{contact_id}",
    unlink_contact,
    methods=["DELETE"],
    status_code=204,
    dependencies=[
        Depends(require_authenticated_request_context),
        Depends(require_csrf),
    ],
)
