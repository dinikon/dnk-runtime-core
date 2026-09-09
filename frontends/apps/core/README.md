# Core frontend

Vue application powered by Nuxt 4 with server-rendered public pages. It is independent from the tenant console.

- `/`: public dNiko Alpha Hero, rendered in the initial HTML with title, description, canonical URL and Open Graph metadata.
- `/app/`: account overview. Session and profile data load only in the browser; unauthenticated users go to Django allauth with the original local path preserved.
- `/accounts/`, `/api/`, `/admin/`, `/static/`: Django Core routes on the same origin.
- `/robots.txt` and `/sitemap.xml`: the sitemap includes only the public homepage. Private pages use `noindex` and `private, no-store` responses.

Run from `frontends/` using Node 24.11 or newer:

```sh
npm ci
npm run build:accounts
npm run dev:core
npm run typecheck:core
npm run lint:core
npm run build:core
```

Development runs at `http://localhost:5174`. `CORE_PROXY_TARGET` defaults to `http://127.0.0.1:8001`; the Nuxt development proxy preserves the browser Host header for same-origin cookies and CSRF. Configure Django's allowed hosts and trusted CSRF origins for the chosen development URL.

Set `NUXT_PUBLIC_SITE_URL` to the canonical external site URL. Its default is `http://localhost:8080`. Public metadata never derives its canonical origin from an incoming Host header.

The production Dockerfile has two targets: `runtime` starts Nitro on port 3000, and `gateway` proxies the public origin through nginx. The gateway forwards the reserved Django paths to Core and all other paths to the Nuxt service. Core serves the shared stylesheet and licensed local Inter fonts at `/static/core/`; both Vue and Django use those exact assets.

Authentication uses server sessions and same-origin cookies. No credentials or session identifiers are persisted in browser storage. The browser fetches a CSRF token from `/api/session/` and attaches `X-CSRFToken` to unsafe API requests. Connection errors show a retry state; only an unauthenticated response triggers a login redirect.

Source boundaries: `src/pages/` contains routes and SEO metadata, `src/middleware/` contains the private-route guard, `src/modules/` contains page features and session state, and `src/shared/` contains the API client and presentation components.

## Browser smoke test

First start the local stack with isolated delivery from the repository root:

```sh
docker compose -f docker-compose.yml -f core/deploy/compose.e2e.yml up -d --build --wait core-frontend
```

Then run from `frontends/`:

```sh
npx playwright install chromium
npm run test:e2e:core
```

`CORE_E2E_BASE_URL` defaults to `http://localhost:8080` and must match Django's `CORE_PUBLIC_ORIGIN`, including hostname and port. The test only accepts a local URL and the Django fixture refuses non-DEBUG settings and real SMTP delivery. Setup creates the dedicated `core_e2e_qa` / `core_e2e_qa@example.invalid` account with a random password and verified fixture email. It refuses to touch an existing account without the exact email and fixture marker. A unique `core_e2e_passkey_<random>@example.invalid` account exercises signup. Teardown removes only those fixture accounts and their session records; it does not change other users or provider credentials.

The Chromium CDP virtual authenticator exercises full passkey signup with email OTP and one-time recovery codes, native forms without JavaScript, mobile errors/password reveal, real passkey enrollment, logout and passkey login, a rejected assertion with its user-verification bit cleared, an aborted browser ceremony, challenge-request failure followed by retry, and the Nuxt API-error recovery screen. CUA does not expose the virtual-authenticator CDP capability, so this suite uses isolated headless Playwright. It does not connect to a user's browser profile or tabs.

Failure screenshots go to the operating system's temporary directory (`dnk-core-e2e-results`), or `CORE_E2E_OUTPUT_DIR`. Traces are disabled to avoid saving session credentials. If the test process is forcibly stopped before teardown, run the guarded cleanup from the repository root:

```sh
docker compose exec -T -e CORE_E2E_OPERATION=cleanup -e CORE_E2E_SIGNUP_USERNAME=core_e2e_passkey_RECORDED_SUFFIX core python src/manage.py shell --no-imports < frontends/apps/core/e2e/fixture_account.py
```


After the test run, restore the normal email backend without editing `.env`:

```sh
docker compose up -d --no-build --no-deps --force-recreate core
```

The shared `@dnk/ui` package contains Shadcn Vue components for Nuxt and Django.
Run `npm run lint:ui`, `npm run typecheck:ui`, and `npm run build:accounts` when
editing it. Django POST forms continue working with the account bundle blocked;
WebAuthn uses allauth's native crypto flow after the components are ready.
