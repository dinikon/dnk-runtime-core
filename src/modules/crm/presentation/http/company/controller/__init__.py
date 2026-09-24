from src.modules.crm.presentation.http.company.controller.create_company import (
    router as create_company_router,
)
from src.modules.crm.presentation.http.company.controller.delete_company import (
    router as delete_company_router,
)
from src.modules.crm.presentation.http.company.controller.get_company import (
    router as get_company_router,
)
from src.modules.crm.presentation.http.company.controller.list_companies import (
    router as list_companies_router,
)
from src.modules.crm.presentation.http.company.controller.update_company import (
    router as update_company_router,
)

__all__ = [
    "create_company_router",
    "delete_company_router",
    "get_company_router",
    "list_companies_router",
    "update_company_router",
]
