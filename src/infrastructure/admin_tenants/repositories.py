from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.admin_tenants.ports.repositories import (
    TenantDomainRepositoryProtocol,
    TenantRepositoryProtocol,
    UserRepositoryProtocol,
)
from src.domain.tenancy.entities import Tenant, TenantDomain
from src.domain.users.entities import User, UserEmail
from src.domain.value_object.tenant_domain_kind import TenantDomainKind
from src.domain.value_object.tenant_domain_tls_mode import TenantDomainTlsMode
from src.domain.value_object.tenant_domain_verification_status import (
    TenantDomainVerificationStatus,
)
from src.domain.value_object.tenant_domian_status import TenantDomainStatus
from src.domain.value_object.tenant_service_type import TenantServiceType
from src.infrastructure.persistence.tenant import TenantModel
from src.infrastructure.persistence.tenant_domain import TenantDomainModel
from src.infrastructure.persistence.user import UserModel
from src.infrastructure.persistence.user_email import UserEmailModel


class SqlAlchemyTenantRepository(TenantRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, tenant: Tenant) -> None:
        self._session.add(
            TenantModel(
                id=tenant.id,
                name=tenant.name,
                status=tenant.status,
                custom_config=tenant.custom_config,
                created_at=tenant.created_at,
                updated_at=tenant.updated_at,
            )
        )
        await self._session.flush()

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        model = await self._session.scalar(
            select(TenantModel).where(TenantModel.id == str(tenant_id))
        )
        if model is None:
            return None
        return self._map_tenant(model)

    async def get_by_name(self, name: str) -> Tenant | None:
        model = await self._session.scalar(
            select(TenantModel).where(TenantModel.name == name)
        )
        if model is None:
            return None
        return self._map_tenant(model)

    async def exists_by_name(self, name: str) -> bool:
        tenant_id = await self._session.scalar(
            select(TenantModel.id).where(TenantModel.name == name).limit(1)
        )
        return tenant_id is not None

    @staticmethod
    def _map_tenant(model: TenantModel) -> Tenant:
        return Tenant(
            id=_to_uuid(model.id),
            name=model.name,
            status=model.status,
            custom_config=model.custom_config,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SqlAlchemyUserRepository(UserRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, user: User) -> None:
        self._session.add(
            UserModel(
                id=user.id,
                tenant_id=user.tenant_id,
                status=user.status,
                last_name=user.last_name,
                first_name=user.first_name,
                middle_name=user.middle_name,
                avatar=user.avatar,
                interface__language=user.interface_language,
                interface_theme=user.interface_theme,
                timezone=user.timezone,
                last_login_at=user.last_login_at,
                last_active_at=user.last_active_at,
                last_login_ip=user.last_login_ip,
                initialized_at=user.initialized_at,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
        )
        for email in user.emails:
            self._session.add(
                UserEmailModel(
                    id=email.id,
                    user_id=email.user_id,
                    email=email.email,
                    is_primary=email.is_primary,
                    is_verified=email.is_verified,
                    is_deleted=email.is_deleted,
                    created_at=email.created_at,
                    updated_at=email.updated_at,
                )
            )
        await self._session.flush()

    async def get_by_id(self, user_id: UUID) -> User | None:
        user_model = await self._session.scalar(
            select(UserModel).where(UserModel.id == str(user_id))
        )
        if user_model is None:
            return None

        email_models = (
            await self._session.scalars(
                select(UserEmailModel).where(UserEmailModel.user_id == str(user_id))
            )
        ).all()
        return self._map_user(user_model, email_models)

    async def exists_by_tenant_and_email(
        self,
        tenant_id: UUID,
        email: str,
    ) -> bool:
        email_id = await self._session.scalar(
            select(UserEmailModel.id)
            .join(UserModel, UserModel.id == UserEmailModel.user_id)
            .where(UserModel.tenant_id == str(tenant_id))
            .where(UserEmailModel.email == email)
            .where(UserEmailModel.is_deleted.is_(False))
            .limit(1)
        )
        return email_id is not None

    @staticmethod
    def _map_user(
        user_model: UserModel, email_models: Sequence[UserEmailModel]
    ) -> User:
        return User(
            id=_to_uuid(user_model.id),
            tenant_id=_to_uuid(user_model.tenant_id),
            status=user_model.status,
            last_name=user_model.last_name,
            first_name=user_model.first_name,
            middle_name=user_model.middle_name,
            avatar=user_model.avatar,
            interface_language=user_model.interface__language,
            interface_theme=user_model.interface_theme,
            timezone=user_model.timezone,
            last_login_at=user_model.last_login_at,
            last_active_at=user_model.last_active_at,
            last_login_ip=user_model.last_login_ip,
            initialized_at=user_model.initialized_at,
            created_at=user_model.created_at,
            updated_at=user_model.updated_at,
            emails=[
                SqlAlchemyUserRepository._map_email(email_model)
                for email_model in email_models
            ],
        )

    @staticmethod
    def _map_email(model: UserEmailModel) -> UserEmail:
        return UserEmail(
            id=_to_uuid(model.id),
            user_id=_to_uuid(model.user_id),
            email=model.email,
            is_primary=model.is_primary,
            is_verified=model.is_verified,
            is_deleted=model.is_deleted,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SqlAlchemyTenantDomainRepository(TenantDomainRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, domain: TenantDomain) -> None:
        self._session.add(
            TenantDomainModel(
                id=domain.id,
                tenant_id=str(domain.tenant_id),
                service_type=domain.service_type,
                kind=domain.kind,
                host=domain.host,
                base_path=domain.base_path,
                auth_mode=domain.auth_mode,
                status=domain.status,
                is_primary=domain.is_primary,
                is_wildcard=domain.is_wildcard,
                parent_domain=domain.parent_domain,
                verification_status=domain.verification_status,
                tls_mode=domain.tls_mode,
                metadata_json=domain.metadata_json,
                created_at=domain.created_at,
                updated_at=domain.updated_at,
            )
        )
        await self._session.flush()

    async def get_by_id(self, domain_id: UUID) -> TenantDomain | None:
        model = await self._session.scalar(
            select(TenantDomainModel).where(TenantDomainModel.id == str(domain_id))
        )
        if model is None:
            return None
        return self._map_domain(model)

    async def get_by_host(self, host: str) -> TenantDomain | None:
        model = await self._session.scalar(
            select(TenantDomainModel).where(TenantDomainModel.host == host)
        )
        if model is None:
            return None
        return self._map_domain(model)

    async def exists_by_host(self, host: str) -> bool:
        domain_id = await self._session.scalar(
            select(TenantDomainModel.id).where(TenantDomainModel.host == host).limit(1)
        )
        return domain_id is not None

    @staticmethod
    def _map_domain(model: TenantDomainModel) -> TenantDomain:
        return TenantDomain(
            id=_to_uuid(model.id),
            tenant_id=_to_uuid(model.tenant_id),
            service_type=TenantServiceType(model.service_type),
            kind=TenantDomainKind(model.kind),
            host=model.host,
            base_path=model.base_path,
            auth_mode=model.auth_mode,
            status=TenantDomainStatus(model.status),
            is_primary=model.is_primary,
            is_wildcard=model.is_wildcard,
            parent_domain=model.parent_domain,
            verification_status=TenantDomainVerificationStatus(
                model.verification_status
            ),
            tls_mode=TenantDomainTlsMode(model.tls_mode),
            metadata_json=model.metadata_json,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


def _to_uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))
