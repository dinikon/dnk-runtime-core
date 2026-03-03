from pydantic import BaseModel, EmailStr


class TenantCreatePartSchema(BaseModel):
    name: str
    external_id: str


class TenantDomainCreatePartSchema(BaseModel):
    host: str


class UserCreatePartSchema(BaseModel):
    last_name: str
    first_name: str


class UserEmailCreatePartSchema(BaseModel):
    email: EmailStr


class AdminCreateTenantRequestSchema(BaseModel):
    tenant: TenantCreatePartSchema
    tenant_domain: TenantDomainCreatePartSchema
    user: UserCreatePartSchema
    user_email: UserEmailCreatePartSchema
