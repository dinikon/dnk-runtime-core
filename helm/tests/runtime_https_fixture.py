"""Seed an isolated fixture, then validate real Runtime OTP/session routes over TLS.

The fixture belongs only to the disposable test cluster. No SMTP message is sent:
we insert the same short-lived Redis challenge the real OTP flow would store.
"""

from http.cookies import SimpleCookie
import json

from cluster import run

SEED = r"""
import sys
sys.path[:0] = ["/app", "/app/src"]
import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID
from sqlalchemy import text
from src.config import dnk_config
from src.modules.shared.infrastructure.persistence.database_helper import db_helper
from src.modules.shared.infrastructure.persistence.tenant_migrations import TenantMigrator
from src.modules.shared.application.persistence.tenant_schema_naming import TenantSchemaNaming
from src.modules.tenancy.domain.tenant.value_object import TenantIdVO
from src.modules.identity.application.auth.service import OtpService
from src.modules.identity.application.ports import OtpChallenge
from src.modules.identity.infrastructure.adapter import TokenManagerBackedOtpChallengeStore
from src.modules.shared.application.tokens import TokenManager
from src.modules.shared.infrastructure.tokens import RedisTokenBackend

async def main():
    tenant = UUID("12345678-1234-4000-8000-000000000001")
    domain = UUID("12345678-1234-4000-8000-000000000002")
    user = UUID("12345678-1234-4000-8000-000000000003")
    email_id = UUID("12345678-1234-4000-8000-000000000004")
    schema = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX).schema_name(TenantIdVO(tenant))
    async with db_helper.engine.begin() as connection:
        await connection.execute(text("INSERT INTO public.tenants (id,name,external_id,status) VALUES (:id,'Helm HTTPS fixture','helm-https-fixture','active') ON CONFLICT (id) DO NOTHING"), {"id": tenant})
        await connection.execute(text("INSERT INTO public.tenant_domains (id,tenant_id,service_type,kind,host,status,is_primary,is_wildcard) VALUES (:id,:tenant,'console','default','runtime.example.test','active',true,false) ON CONFLICT (id) DO NOTHING"), {"id": domain,"tenant":tenant})
        await connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        await TenantMigrator().upgrade(connection, schema)
        await connection.execute(text(f'INSERT INTO "{schema}".users (id,user_type,last_name,first_name,last_active_at) VALUES (:id,\'admin\',\'Fixture\',\'Helm\',CURRENT_TIMESTAMP) ON CONFLICT (id) DO NOTHING'), {"id":user})
        await connection.execute(text(f'INSERT INTO "{schema}".user_emails (id,user_id,email,is_primary,is_verified) VALUES (:id,:user,\'helm-auth@example.com\',true,false) ON CONFLICT (id) DO NOTHING'), {"id":email_id,"user":user})
    otp = OtpService(dnk_config.AUTH.otp_code_length).generate()
    store = TokenManagerBackedOtpChallengeStore(TokenManager(RedisTokenBackend.from_config()))
    await store.create_challenge(OtpChallenge(token=otp.token, email="helm-auth@example.com", tenant_id=tenant, tenant_domain_id=domain, host="runtime.example.test", code_hash=otp.code_hash, created_at=otp.created_at), 300)
    await db_helper.engine.dispose()
    print(json.dumps({"email":"helm-auth@example.com", "token":otp.token, "code":otp.code, "user_id":str(user), "cookie":dnk_config.AUTH.session_cookie_name}))

asyncio.run(main())
"""


def check_runtime_auth(cluster, proxy):
    port, certificate = proxy
    deployment = cluster.name_for("deployment", "runtime", "backend")
    result = cluster.kubectl(
        "exec",
        "deployment/" + deployment,
        "-c",
        "backend",
        "--",
        "python",
        "/opt/dnk-runtime/entrypoint.py",
        "python",
        "-c",
        SEED,
        capture=True,
    )
    seeded = json.loads(result.stdout.strip().splitlines()[-1])
    cookie_name = seeded.pop("cookie")
    expected_user_id = seeded.pop("user_id")
    request_path = cluster.work / "runtime-auth-request.json"
    request_path.write_text(json.dumps(seeded))
    cookie_path = cluster.work / "runtime-auth-cookies.txt"
    cookie_path.unlink(missing_ok=True)
    headers_path = cluster.work / "runtime-auth-headers.txt"
    body_path = cluster.work / "runtime-auth-body.json"

    def request(path, *, method="GET", data=None):
        args = [
            "curl",
            "--silent",
            "--show-error",
            "--noproxy",
            "*",
            "--cacert",
            str(certificate),
            "--resolve",
            f"runtime.example.test:{port}:127.0.0.1",
            "--max-time",
            "30",
            "--request",
            method,
            "--cookie",
            str(cookie_path),
            "--cookie-jar",
            str(cookie_path),
            "--dump-header",
            str(headers_path),
            "--output",
            str(body_path),
            "--write-out",
            "%{http_code}",
        ]
        if data:
            args += [
                "--header",
                "Content-Type: application/json",
                "--data-binary",
                "@" + str(data),
            ]
        args.append(f"https://runtime.example.test:{port}/api/console/auth{path}")
        response = run(args, capture=True)
        return int(response.stdout), json.loads(body_path.read_text())

    status, body = request("/confirm-otp", method="POST", data=request_path)
    assert status == 200 and body.get("ok"), (status, body)
    assert body["user_id"] == expected_user_id
    cookies = SimpleCookie()
    for line in headers_path.read_text().splitlines():
        if line.lower().startswith("set-cookie:"):
            cookies.load(line.split(":", 1)[1].strip())
    session = cookies[cookie_name]
    assert (
        session["secure"]
        and session["httponly"]
        and session["samesite"].lower() == "lax"
    )
    status, body = request("/me")
    assert status == 200 and body["id"] == expected_user_id, (status, body)
    assert any(
        email["email"] == seeded["email"] and email["is_verified"]
        for email in body["emails"]
    )
    status, body = request("/logout", method="POST")
    assert status == 200 and body.get("ok"), (status, body)
    status, body = request("/me")
    assert status == 401, (status, body)
    print(
        "PASS: Runtime OTP login, Secure/HttpOnly/SameSite cookie, /me and logout over HTTPS",
        flush=True,
    )
