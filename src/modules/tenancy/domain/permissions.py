from enum import StrEnum


class TenancyAction(StrEnum):
    """Действия authorization policy для tenancy-модуля."""

    ADMIN_CREATE_TENANT = "tenancy.admin.create_tenant"
