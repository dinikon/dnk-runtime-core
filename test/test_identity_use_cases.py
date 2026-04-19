from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.modules.identity.application import SessionRecord, TenantRequestContext
from src.modules.identity.application.auth import (
    AuthenticateBySessionCommand,
    AuthenticateBySessionUseCase,
    ConfirmEmailOtpCommandDTO,
    ConfirmEmailOtpUseCase,
    GetCurrentUserCommandDTO,
    GetCurrentUserUseCase,
    LogoutCurrentSessionCommandDTO,
    LogoutCurrentSessionUseCase,
    OtpService,
    RequestEmailOtpCommandDTO,
    RequestEmailOtpUseCase,
    SessionService,
    UpdateCurrentUserProfileCommandDTO,
    UpdateCurrentUserProfileUseCase,
)
from src.modules.identity.application.user import UserService
from src.modules.identity.domain import (
    InvalidOtpChallengeError,
    InvalidOtpCodeError,
    InvalidSessionError,
    UserEmailAlreadyExistsError,
    User,
)
from src.modules.shared.domain.errors import DomainError
from src.modules.shared.kernel.email import (
    EmailDeliveryError,
    SystemEmailKind,
)


class _TenantContextReaderStub:
    def __init__(self, context: TenantRequestContext):
        self.context = context

    async def get_by_host(self, host: str) -> TenantRequestContext:
        return self.context


class _UnitOfWorkStub:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class _EmailServiceStub:
    def __init__(self) -> None:
        self.sent: list[tuple[SystemEmailKind, str, dict[str, str]]] = []

    async def send(self, kind, recipient_email: str, variables) -> None:
        self.sent.append((kind, recipient_email, dict(variables)))


class _FailingEmailServiceStub:
    async def send(self, kind, recipient_email: str, variables) -> None:
        raise EmailDeliveryError("SMTP is unavailable.")


class _OtpChallengeStoreStub:
    def __init__(self) -> None:
        self.created = None
        self.invalidated: list[tuple[object, str]] = []
        self.challenge = None

    async def create_challenge(self, challenge, ttl_seconds: int) -> None:
        self.created = (challenge, ttl_seconds)
        self.challenge = challenge

    async def get_challenge(self, tenant_id, token: str):
        return self.challenge

    async def invalidate_challenge(self, tenant_id, token: str) -> None:
        self.invalidated.append((tenant_id, token))


class _SessionStoreStub:
    def __init__(self) -> None:
        self.created = None
        self.invalidated: list[tuple[object, str]] = []
        self.session = None

    async def create_session(self, session: SessionRecord, ttl_seconds: int) -> None:
        self.created = (session, ttl_seconds)
        self.session = session

    async def get_session(self, tenant_id, token: str):
        return self.session

    async def invalidate_session(self, tenant_id, token: str) -> None:
        self.invalidated.append((tenant_id, token))


class _UserRepositoryStub:
    def __init__(self, user: User | None = None) -> None:
        self.user = user
        self.updated_profile = None
        self.marked_email_ids: list[object] = []
        self.added_users: list[User] = []
        self.exists = False

    async def add(self, user: User) -> None:
        self.added_users.append(user)

    async def get_by_id(self, user_id):
        if self.user is not None and self.user.id == user_id:
            return self.user
        return self.user

    async def get_by_tenant_and_primary_email(self, tenant_id, email: str):
        if self.user is None:
            return None
        if self.user.tenant_id != tenant_id:
            return None
        return self.user if self.user.get_primary_email(email) is not None else None

    async def update_profile(self, user: User) -> None:
        self.updated_profile = user

    async def mark_email_verified(self, user_email_id) -> None:
        self.marked_email_ids.append(user_email_id)

    async def exists_by_tenant_and_email(self, tenant_id, email: str) -> bool:
        return self.exists


class IdentityUseCaseTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tenant_id = uuid4()
        self.tenant_domain_id = uuid4()
        self.context = TenantRequestContext(
            tenant_id=self.tenant_id,
            tenant_domain_id=self.tenant_domain_id,
            host="tenant.example.com",
            tenant_status="active",
            domain_status="active",
            api_host="api.tenant.example.com",
        )

    async def test_request_email_otp_creates_challenge_and_sends_code(self) -> None:
        user = User.create_tenant_admin(
            tenant_id=self.tenant_id,
            first_name="John",
            last_name="Doe",
        )
        user.add_email("john@example.com", is_primary=True)
        users_repository = _UserRepositoryStub(user)
        challenge_store = _OtpChallengeStoreStub()
        email_service = _EmailServiceStub()

        use_case = RequestEmailOtpUseCase(
            tenant_context_reader=_TenantContextReaderStub(self.context),
            users_repository=users_repository,
            otp_challenge_store=challenge_store,
            otp_service=OtpService(6),
            email_service=email_service,
            otp_ttl_seconds=300,
        )

        result = await use_case(
            RequestEmailOtpCommandDTO(
                host=self.context.host,
                email="john@example.com",
            )
        )

        self.assertTrue(result.token.startswith("otp_"))
        self.assertEqual(result.expires_in, 300)
        self.assertIsNotNone(result.code)
        self.assertEqual(challenge_store.created[0].email, "john@example.com")
        self.assertEqual(challenge_store.created[1], 300)
        self.assertEqual(email_service.sent[0][0], SystemEmailKind.SEND_OTP_CODE)
        self.assertEqual(email_service.sent[0][1], "john@example.com")
        self.assertEqual(email_service.sent[0][2]["otp_code"], result.code)

    async def test_request_email_otp_keeps_success_when_email_delivery_fails(
        self,
    ) -> None:
        user = User.create_tenant_admin(
            tenant_id=self.tenant_id,
            first_name="John",
            last_name="Doe",
        )
        user.add_email("john@example.com", is_primary=True)
        challenge_store = _OtpChallengeStoreStub()

        use_case = RequestEmailOtpUseCase(
            tenant_context_reader=_TenantContextReaderStub(self.context),
            users_repository=_UserRepositoryStub(user),
            otp_challenge_store=challenge_store,
            otp_service=OtpService(6),
            email_service=_FailingEmailServiceStub(),
            otp_ttl_seconds=300,
        )

        result = await use_case(
            RequestEmailOtpCommandDTO(
                host=self.context.host,
                email="john@example.com",
            )
        )

        self.assertTrue(result.token.startswith("otp_"))
        self.assertEqual(result.expires_in, 300)
        self.assertEqual(challenge_store.created[0].email, "john@example.com")
        self.assertEqual(challenge_store.invalidated, [])

    async def test_confirm_email_otp_verifies_email_and_creates_session(self) -> None:
        user = User.create_tenant_admin(
            tenant_id=self.tenant_id,
            first_name="John",
            last_name="Doe",
        )
        primary_email = user.add_email("john@example.com", is_primary=True)
        users_repository = _UserRepositoryStub(user)
        challenge_store = _OtpChallengeStoreStub()
        otp_service = OtpService(6)
        generated = otp_service.generate()
        challenge_store.challenge = type(
            "Challenge",
            (),
            {
                "token": generated.token,
                "email": "john@example.com",
                "tenant_id": self.tenant_id,
                "tenant_domain_id": self.tenant_domain_id,
                "host": self.context.host,
                "code_hash": generated.code_hash,
                "created_at": generated.created_at,
            },
        )()
        session_store = _SessionStoreStub()
        uow = _UnitOfWorkStub()

        use_case = ConfirmEmailOtpUseCase(
            uow=uow,
            tenant_context_reader=_TenantContextReaderStub(self.context),
            users_repository=users_repository,
            otp_challenge_store=challenge_store,
            session_store=session_store,
            otp_service=otp_service,
            session_service=SessionService(),
            session_ttl_seconds=600,
        )

        result = await use_case(
            ConfirmEmailOtpCommandDTO(
                host=self.context.host,
                email="john@example.com",
                token=generated.token,
                code=generated.code,
            )
        )

        self.assertTrue(result.ok)
        self.assertTrue(uow.committed)
        self.assertFalse(uow.rolled_back)
        self.assertTrue(primary_email.is_verified)
        self.assertEqual(users_repository.marked_email_ids, [primary_email.id])
        self.assertEqual(
            challenge_store.invalidated, [(self.tenant_id, generated.token)]
        )
        self.assertIsNotNone(session_store.created)
        self.assertEqual(session_store.created[1], 600)

    async def test_confirm_email_otp_rejects_invalid_code(self) -> None:
        user = User.create_tenant_admin(
            tenant_id=self.tenant_id,
            first_name="John",
            last_name="Doe",
        )
        user.add_email("john@example.com", is_primary=True)
        otp_service = OtpService(6)
        generated = otp_service.generate()
        challenge_store = _OtpChallengeStoreStub()
        challenge_store.challenge = type(
            "Challenge",
            (),
            {
                "token": generated.token,
                "email": "john@example.com",
                "tenant_id": self.tenant_id,
                "tenant_domain_id": self.tenant_domain_id,
                "host": self.context.host,
                "code_hash": generated.code_hash,
                "created_at": generated.created_at,
            },
        )()

        use_case = ConfirmEmailOtpUseCase(
            uow=_UnitOfWorkStub(),
            tenant_context_reader=_TenantContextReaderStub(self.context),
            users_repository=_UserRepositoryStub(user),
            otp_challenge_store=challenge_store,
            session_store=_SessionStoreStub(),
            otp_service=otp_service,
            session_service=SessionService(),
            session_ttl_seconds=600,
        )

        with self.assertRaises(InvalidOtpCodeError):
            await use_case(
                ConfirmEmailOtpCommandDTO(
                    host=self.context.host,
                    email="john@example.com",
                    token=generated.token,
                    code="000000",
                )
            )

    async def test_confirm_email_otp_rejects_missing_challenge(self) -> None:
        user = User.create_tenant_admin(
            tenant_id=self.tenant_id,
            first_name="John",
            last_name="Doe",
        )
        user.add_email("john@example.com", is_primary=True)

        use_case = ConfirmEmailOtpUseCase(
            uow=_UnitOfWorkStub(),
            tenant_context_reader=_TenantContextReaderStub(self.context),
            users_repository=_UserRepositoryStub(user),
            otp_challenge_store=_OtpChallengeStoreStub(),
            session_store=_SessionStoreStub(),
            otp_service=OtpService(6),
            session_service=SessionService(),
            session_ttl_seconds=600,
        )

        with self.assertRaises(InvalidOtpChallengeError):
            await use_case(
                ConfirmEmailOtpCommandDTO(
                    host=self.context.host,
                    email="john@example.com",
                    token="missing-token",
                    code="123456",
                )
            )

    async def test_authenticate_by_session_restores_principal(self) -> None:
        user = User.create_tenant_admin(
            tenant_id=self.tenant_id,
            first_name="John",
            last_name="Doe",
        )
        user.add_email("john@example.com", is_primary=True)
        session_store = _SessionStoreStub()
        now = datetime.now(UTC)
        session_store.session = SessionRecord(
            token="sess-token",
            session_id="session-id",
            user_id=user.id,
            tenant_id=self.tenant_id,
            tenant_domain_id=self.tenant_domain_id,
            host=self.context.host,
            issued_at=now,
            expires_at=now + timedelta(hours=1),
        )

        use_case = AuthenticateBySessionUseCase(
            tenant_context_reader=_TenantContextReaderStub(self.context),
            users_repository=_UserRepositoryStub(user),
            session_store=session_store,
        )

        result = await use_case(
            AuthenticateBySessionCommand(
                host=self.context.host,
                session_token="sess-token",
                ip="127.0.0.1",
                user_agent="pytest",
            )
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.user_id, str(user.id))
        self.assertEqual(result.tenant_id, str(self.tenant_id))
        self.assertEqual(result.session_id, "session-id")

    async def test_get_current_user_raises_for_missing_session_token(self) -> None:
        use_case = GetCurrentUserUseCase(
            tenant_context_reader=_TenantContextReaderStub(self.context),
            users_repository=_UserRepositoryStub(),
            session_store=_SessionStoreStub(),
        )

        with self.assertRaises(InvalidSessionError):
            await use_case(
                GetCurrentUserCommandDTO(
                    host=self.context.host,
                    session_token=None,
                )
            )

    async def test_update_current_user_profile_persists_changes(self) -> None:
        user = User.create_tenant_admin(
            tenant_id=self.tenant_id,
            first_name="John",
            last_name="Doe",
        )
        user.add_email("john@example.com", is_primary=True, is_verified=True)
        users_repository = _UserRepositoryStub(user)
        session_store = _SessionStoreStub()
        now = datetime.now(UTC)
        session_store.session = SessionRecord(
            token="sess-token",
            session_id="session-id",
            user_id=user.id,
            tenant_id=self.tenant_id,
            tenant_domain_id=self.tenant_domain_id,
            host=self.context.host,
            issued_at=now,
            expires_at=now + timedelta(hours=1),
        )
        uow = _UnitOfWorkStub()

        use_case = UpdateCurrentUserProfileUseCase(
            uow=uow,
            tenant_context_reader=_TenantContextReaderStub(self.context),
            users_repository=users_repository,
            session_store=session_store,
        )

        result = await use_case(
            UpdateCurrentUserProfileCommandDTO(
                host=self.context.host,
                session_token="sess-token",
                last_name="Smith",
                first_name="Jane",
                middle_name="A",
                interface_language="en",
                interface_theme="dark",
                timezone="Europe/Warsaw",
            )
        )

        self.assertTrue(uow.committed)
        self.assertEqual(result.last_name, "Smith")
        self.assertEqual(result.first_name, "Jane")
        self.assertEqual(result.interface_language, "en")
        self.assertEqual(result.interface_theme, "dark")
        self.assertIs(users_repository.updated_profile, user)

    async def test_update_current_user_profile_rejects_none_interface_theme(
        self,
    ) -> None:
        user = User.create_tenant_admin(
            tenant_id=self.tenant_id,
            first_name="John",
            last_name="Doe",
        )
        user.add_email("john@example.com", is_primary=True, is_verified=True)
        users_repository = _UserRepositoryStub(user)
        session_store = _SessionStoreStub()
        now = datetime.now(UTC)
        session_store.session = SessionRecord(
            token="sess-token",
            session_id="session-id",
            user_id=user.id,
            tenant_id=self.tenant_id,
            tenant_domain_id=self.tenant_domain_id,
            host=self.context.host,
            issued_at=now,
            expires_at=now + timedelta(hours=1),
        )
        uow = _UnitOfWorkStub()

        use_case = UpdateCurrentUserProfileUseCase(
            uow=uow,
            tenant_context_reader=_TenantContextReaderStub(self.context),
            users_repository=users_repository,
            session_store=session_store,
        )

        with self.assertRaises(DomainError):
            await use_case(
                UpdateCurrentUserProfileCommandDTO(
                    host=self.context.host,
                    session_token="sess-token",
                    last_name="Smith",
                    first_name="Jane",
                    middle_name="A",
                    interface_language="en",
                    interface_theme=None,
                    timezone="Europe/Warsaw",
                )
            )

        self.assertFalse(uow.committed)
        self.assertFalse(uow.rolled_back)

    async def test_logout_current_session_invalidates_matching_session(self) -> None:
        session_store = _SessionStoreStub()
        now = datetime.now(UTC)
        session_store.session = SessionRecord(
            token="sess-token",
            session_id="session-id",
            user_id=uuid4(),
            tenant_id=self.tenant_id,
            tenant_domain_id=self.tenant_domain_id,
            host=self.context.host,
            issued_at=now,
            expires_at=now + timedelta(hours=1),
        )
        use_case = LogoutCurrentSessionUseCase(
            tenant_context_reader=_TenantContextReaderStub(self.context),
            session_store=session_store,
        )

        result = await use_case(
            LogoutCurrentSessionCommandDTO(
                host=self.context.host,
                session_token="sess-token",
            )
        )

        self.assertTrue(result.ok)
        self.assertEqual(session_store.invalidated, [(self.tenant_id, "sess-token")])

    async def test_user_service_creates_tenant_admin(self) -> None:
        users_repository = _UserRepositoryStub()
        service = UserService(users_repository)

        result = await service.create_tenant_admin(
            tenant_id=self.tenant_id,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
        )

        self.assertEqual(len(users_repository.added_users), 1)
        created_user = users_repository.added_users[0]
        self.assertEqual(created_user.first_name, "John")
        self.assertEqual(created_user.last_name, "Doe")
        self.assertEqual(
            created_user.get_primary_email("john@example.com").id, result.user_email_id
        )
        self.assertEqual(result.user_status, "active")

    async def test_user_service_rejects_duplicate_email(self) -> None:
        users_repository = _UserRepositoryStub()
        users_repository.exists = True
        service = UserService(users_repository)

        with self.assertRaises(UserEmailAlreadyExistsError):
            await service.create_tenant_admin(
                tenant_id=self.tenant_id,
                first_name="John",
                last_name="Doe",
                email="john@example.com",
            )


__all__ = ["IdentityUseCaseTests"]
