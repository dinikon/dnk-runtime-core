from pydantic import BaseModel, EmailStr


class TenantCreatePartSchema(BaseModel):
    """Pydantic-схема части запроса с tenant metadata."""

    name: str
    external_id: str


class TenantDomainCreatePartSchema(BaseModel):
    """Pydantic-схема части запроса с primary domain tenant."""

    host: str


class UserCreatePartSchema(BaseModel):
    """Pydantic-схема части запроса с ФИО tenant admin."""

    last_name: str
    first_name: str


class UserEmailCreatePartSchema(BaseModel):
    """Pydantic-схема части запроса с email tenant admin."""

    email: EmailStr


class AdminCreateTenantRequestSchema(BaseModel):
    """Pydantic-схема запроса создания tenant через admin endpoint."""

    tenant: TenantCreatePartSchema
    tenant_domain: TenantDomainCreatePartSchema
    user: UserCreatePartSchema
    user_email: UserEmailCreatePartSchema
